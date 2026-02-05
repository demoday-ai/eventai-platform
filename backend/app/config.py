from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://demoday:demoday@localhost:5432/demoday"
    bot_token: str = ""
    bot_mode: str = "polling"  # "polling" or "webhook"
    organizer_telegram_ids: str = ""
    organizer_telegram_usernames: str = ""  # comma-separated usernames (without @)
    secret_key: str = "dev-secret-key"
    webhook_url: str = ""  # e.g. https://team10.camp.aitalenthub.ru
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4.1"
    team_chat_id: str = ""  # Telegram chat ID for lead notifications
    team_bot_token: str = ""  # Separate bot token for team notifications (optional)

    @property
    def organizer_ids(self) -> set[str]:
        if not self.organizer_telegram_ids:
            return set()
        return {tid.strip() for tid in self.organizer_telegram_ids.split(",")}

    @property
    def organizer_usernames(self) -> set[str]:
        if not self.organizer_telegram_usernames:
            return set()
        return {u.strip().lower().lstrip("@") for u in self.organizer_telegram_usernames.split(",")}

    def is_organizer(self, user_id: int | str, username: str | None = None) -> bool:
        """Check if user is organizer by ID or username."""
        if str(user_id) in self.organizer_ids:
            return True
        if username and username.lower().lstrip("@") in self.organizer_usernames:
            return True
        return False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
