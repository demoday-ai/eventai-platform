#!/usr/bin/env python3
"""
Parse project information from AI Talent Camp dashboard.

Fetches README content from each team page and exports to CSV format
compatible with EventAI project upload.
"""

import asyncio
import csv
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://camp.aitalenthub.ru"
TEAMS = [f"team{i:02d}" for i in range(18)]  # team00 - team17
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "camp_projects.csv"


async def fetch_team_page(client: httpx.AsyncClient, team_id: str) -> str | None:
    """Fetch team page HTML."""
    url = f"{BASE_URL}/team/{team_id}"
    try:
        response = await client.get(url, timeout=30.0)
        if response.status_code == 200:
            return response.text
        print(f"  {team_id}: HTTP {response.status_code}")
        return None
    except Exception as e:
        print(f"  {team_id}: Error - {e}")
        return None


def extract_readme_content(html: str) -> str | None:
    """Extract README content from page HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Look for README section - typically in a markdown-rendered div
    # Try different selectors based on common patterns
    readme_selectors = [
        ".readme-content",
        ".markdown-body",
        "[data-readme]",
        ".prose",
        "article",
        ".readme",
    ]

    for selector in readme_selectors:
        element = soup.select_one(selector)
        if element:
            return element.get_text(separator="\n", strip=True)

    # Fallback: look for largest text block
    main = soup.select_one("main") or soup.body
    if main:
        return main.get_text(separator="\n", strip=True)

    return None


def parse_project_info(readme_text: str, team_id: str) -> dict:
    """Parse project info from README text."""
    info = {
        "title": "",
        "description": "",
        "author": "",
        "telegram_contact": "",
        "tags": "",  # Leave empty for auto-extraction in upload pipeline
    }

    lines = readme_text.split("\n")
    lines = [line.strip() for line in lines if line.strip()]

    # Try to extract title (usually first heading or project name)
    for line in lines[:10]:
        # Skip common headers
        if line.lower() in ["readme", "readme.md", "#", "##"]:
            continue
        # Look for project name patterns
        clean = re.sub(r'^[#\s*]+', '', line).strip()
        if clean and len(clean) > 3 and len(clean) < 200:
            info["title"] = clean
            break

    # If no title found, use team_id
    if not info["title"]:
        info["title"] = f"Project {team_id}"

    # Extract description - combine meaningful paragraphs
    desc_lines = []
    skip_sections = ["установка", "install", "usage", "запуск", "requirements",
                     "лицензия", "license", "contributing", "deploy", "api"]
    in_skip_section = False

    for line in lines:
        lower = line.lower()

        # Check if entering a skip section
        if any(skip in lower for skip in skip_sections) and (line.startswith("#") or line.startswith("**")):
            in_skip_section = True
            continue

        # Reset skip on new major section
        if line.startswith("# ") and not any(skip in lower for skip in skip_sections):
            in_skip_section = False

        if in_skip_section:
            continue

        # Skip short lines, headers we already processed, badges, links
        if len(line) < 20:
            continue
        if line.startswith("![") or line.startswith("[!["):
            continue
        if line.startswith("http://") or line.startswith("https://"):
            continue
        if line.startswith("|"):  # table
            continue

        # Clean markdown formatting
        clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)  # links
        clean = re.sub(r'[*_`#]+', '', clean).strip()

        if clean and len(clean) > 20:
            desc_lines.append(clean)

        # Limit description length
        if len(" ".join(desc_lines)) > 1500:
            break

    info["description"] = " ".join(desc_lines[:10])[:2000]

    if not info["description"]:
        info["description"] = f"Проект команды {team_id} AI Talent Camp 2026"

    # Extract telegram contacts
    telegram_pattern = r'@[\w_]{5,32}'
    telegrams = re.findall(telegram_pattern, readme_text)
    if telegrams:
        # Filter out common bot names
        telegrams = [t for t in telegrams if not t.lower().endswith("bot")]
        if telegrams:
            info["telegram_contact"] = telegrams[0]

    if not info["telegram_contact"]:
        info["telegram_contact"] = "@unknown"

    # Extract author/team info
    author_patterns = [
        r'(?:автор|author|team|команда|разработ)[:\s]+([^\n]+)',
        r'(?:created by|made by|by)[:\s]+([^\n]+)',
    ]

    for pattern in author_patterns:
        match = re.search(pattern, readme_text, re.IGNORECASE)
        if match:
            author = match.group(1).strip()
            author = re.sub(r'[*_`\[\]]+', '', author)[:300]
            if author and len(author) > 2:
                info["author"] = author
                break

    if not info["author"]:
        info["author"] = f"Команда {team_id}"

    return info


async def parse_all_teams() -> list[dict]:
    """Parse all team projects."""
    projects = []

    async with httpx.AsyncClient() as client:
        print(f"Fetching {len(TEAMS)} team pages...")

        for team_id in TEAMS:
            print(f"  Processing {team_id}...")
            html = await fetch_team_page(client, team_id)

            if not html:
                continue

            readme = extract_readme_content(html)
            if not readme:
                print(f"  {team_id}: No README found")
                continue

            project = parse_project_info(readme, team_id)
            project["team_id"] = team_id  # Keep for reference
            projects.append(project)
            print(f"    -> {project['title'][:50]}...")

            # Small delay to be polite
            await asyncio.sleep(0.3)

    return projects


def save_to_csv(projects: list[dict], output_path: Path):
    """Save projects to CSV in upload-compatible format."""
    # CSV columns required for upload
    fieldnames = ["title", "description", "author", "telegram_contact", "tags"]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for project in projects:
            # Only write required fields
            row = {field: project.get(field, "") for field in fieldnames}
            writer.writerow(row)

    print(f"\nSaved {len(projects)} projects to {output_path}")


async def main():
    """Main entry point."""
    print("AI Talent Camp Projects Parser")
    print("=" * 40)

    projects = await parse_all_teams()

    if projects:
        save_to_csv(projects, OUTPUT_FILE)

        # Print summary
        print("\nSummary:")
        print(f"  Total teams: {len(TEAMS)}")
        print(f"  Parsed projects: {len(projects)}")
        print(f"  Output: {OUTPUT_FILE}")
    else:
        print("\nNo projects parsed!")


if __name__ == "__main__":
    asyncio.run(main())
