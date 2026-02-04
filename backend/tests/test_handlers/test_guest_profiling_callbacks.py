import re

from telegram.ext import CallbackQueryHandler

from app.bot.handlers.guest_profiling import CONFIRM_PROFILE, get_profiling_handler
from app.bot.keyboards import confirm_interests_keyboard


def test_confirm_interests_callbacks_match_handler():
    handler = get_profiling_handler()
    state_handlers = handler.states[CONFIRM_PROFILE]
    patterns = [
        h.pattern
        for h in state_handlers
        if isinstance(h, CallbackQueryHandler) and h.pattern is not None
    ]
    assert patterns, "No callback patterns found for CONFIRM_PROFILE state"

    pattern = patterns[0]
    regex = re.compile(pattern.pattern if hasattr(pattern, "pattern") else pattern)

    keyboard = confirm_interests_keyboard()
    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data
    ]

    for callback_data in callbacks:
        assert regex.match(callback_data), f"Callback '{callback_data}' does not match {regex.pattern}"
