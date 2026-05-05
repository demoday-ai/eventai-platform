import importlib


def test_backend_smoke_imports():
    """Smoke check that backend modules import cleanly after 031-bot-replacement.

    The legacy app.bot package was removed; bot lives in the standalone bot/ service.
    Backend imports only the send-only aiogram messenger plus its scheduler.
    """
    modules = [
        "app.main",
        "app.lifespan",
        "app.scheduler",
        "app.services.core.bot_messenger",
    ]
    for module in modules:
        importlib.import_module(module)
