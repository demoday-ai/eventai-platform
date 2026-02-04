import importlib


def test_backend_smoke_imports():
    modules = [
        "app.main",
        "app.bot.keyboards",
        "app.bot.handlers.guest_profiling",
    ]
    for module in modules:
        importlib.import_module(module)
