from pydantic import BaseModel


class ProfileTurn(BaseModel):
    """Profiling dialogue turn (action=reply continues dialog, action=profile = extracted)."""

    action: str = "reply"
    message: str | None = None
    interests: list[str] | None = None
    goals: list[str] | None = None
    summary: str | None = None
    company: str | None = None
    position: str | None = None
    business_objectives: list[str] | None = None


class RerankGrade(BaseModel):
    index: int
    grade: str  # "strong" | "weak" | "off"
    reason: str = ""


class RerankResult(BaseModel):
    grades: list[RerankGrade] = []


class ComparisonResult(BaseModel):
    matrix: dict[str, dict[str, str]] = {}


class QnAResult(BaseModel):
    questions: list[str] = []


class RedFlag(BaseModel):
    category: str      # "metric", "team", "scope", "technical"
    description: str
    severity: str      # "low", "medium", "high"


class ProjectExtraction(BaseModel):
    # Core
    problem: str
    solution: str
    audience: str
    stack: list[str]
    novelty: str
    risks: str | None = None

    # Metrics
    key_metrics: list[str] | None = None        # ["F1=0.91", "94% accuracy"]
    production_readiness: str | None = None      # "prototype" | "mvp" | "production"

    # Team
    team_size: int | None = None

    # Red flags
    red_flags: list[RedFlag] | None = None
