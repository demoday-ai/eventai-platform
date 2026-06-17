from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Bot
    bot_token: str
    bot_mode: str = "polling"  # polling or webhook

    # Platform
    platform_url: str = "http://localhost:8000"
    master_token: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://eventai:eventai@localhost:5432/eventai"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_password: str = ""

    # LLM
    llm_model: str = "deepseek/deepseek-v4-flash"
    embedding_model: str = "google/gemini-embedding-001"
    openrouter_api_key: str = ""  # for standalone mode (no llm-agent-platform)

    # GitHub
    github_token: str = ""  # GitHub token for API access via gh CLI

    # Limits
    rate_limit_per_minute: int = 10
    semaphore_limit: int = 10
    # Budget for one full agent.run. Must exceed the worst nested chain:
    # agent reasoning turn + a tool that itself makes a full LLM call
    # (compare 25s / questions 20s) + a formatting turn. 45s tripped on cold
    # starts and produced false "Обработка занимает больше времени".
    agent_timeout: float = 75.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
