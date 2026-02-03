"""GitHub service for EPIC-008: Expert Project Overview.

Fetches repository status (last commit date) from GitHub API.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# GitHub API timeout
GITHUB_TIMEOUT = 5.0


@dataclass
class GitHubStatus:
    """GitHub repository status."""

    exists: bool
    last_commit: datetime | None = None
    error: str | None = None

    @property
    def display(self) -> str:
        """Format status for display in briefing card."""
        if self.error:
            return f"⚠️ {self.error}"
        if not self.exists:
            return "—"
        if self.last_commit:
            date_str = self.last_commit.strftime("%d.%m.%Y")
            return f"✓ обновлён {date_str}"
        return "✓"


def parse_github_url(url: str) -> tuple[str, str] | None:
    """Extract owner and repo from GitHub URL.

    Supports:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - github.com/owner/repo

    Returns (owner, repo) or None if invalid.
    """
    if not url:
        return None

    # Normalize URL
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    # Match GitHub URL pattern
    pattern = r"(?:https?://)?github\.com/([^/]+)/([^/]+)"
    match = re.match(pattern, url)
    if match:
        return match.group(1), match.group(2)
    return None


async def get_repo_status(github_url: str | None) -> GitHubStatus:
    """Fetch repository status from GitHub API.

    Args:
        github_url: GitHub repository URL

    Returns:
        GitHubStatus with exists flag and optional last commit date
    """
    if not github_url:
        return GitHubStatus(exists=False)

    parsed = parse_github_url(github_url)
    if not parsed:
        return GitHubStatus(exists=False, error="неверный URL")

    owner, repo = parsed
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    try:
        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
            response = await client.get(
                api_url,
                headers={"Accept": "application/vnd.github.v3+json"},
            )

            if response.status_code == 404:
                return GitHubStatus(exists=False)

            if response.status_code == 403:
                # Rate limited
                logger.warning("GitHub API rate limit exceeded")
                return GitHubStatus(exists=True, error="лимит запросов")

            if response.status_code != 200:
                logger.warning("GitHub API error: %d", response.status_code)
                return GitHubStatus(exists=True, error="недоступен")

            data = response.json()
            pushed_at = data.get("pushed_at")
            last_commit = None
            if pushed_at:
                last_commit = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))

            return GitHubStatus(exists=True, last_commit=last_commit)

    except httpx.TimeoutException:
        logger.warning("GitHub API timeout for %s/%s", owner, repo)
        return GitHubStatus(exists=True, error="таймаут")
    except Exception as e:
        logger.error("GitHub API error: %s", e)
        return GitHubStatus(exists=True, error="ошибка")
