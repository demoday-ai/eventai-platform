from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://demoday:demoday@localhost:5432/demoday"
    bot_token: str = ""
    bot_mode: str = "polling"  # "polling" or "webhook"
    organizer_telegram_ids: str = ""
    secret_key: str = "dev-secret-key"
    webhook_url: str = ""  # e.g. https://team10.camp.aitalenthub.ru

    @property
    def organizer_ids(self) -> set[str]:
        if not self.organizer_telegram_ids:
            return set()
        return {tid.strip() for tid in self.organizer_telegram_ids.split(",")}

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
