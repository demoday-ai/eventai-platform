import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.api.auth import _verify_telegram_login
from app.config import settings
from app.schemas.user import TelegramAuthRequest


@pytest.fixture(autouse=True)
def set_bot_token(monkeypatch):
    monkeypatch.setattr(settings, "bot_token", "test-bot-token")


def _sign_payload(**kwargs):
    payload_fields = {"auth_date": str(kwargs["auth_date"]), "id": kwargs["telegram_user_id"]}
    for key in ("first_name", "last_name", "username", "photo_url"):
        value = kwargs.get(key)
        if value:
            payload_fields[key] = value

    data_check_string = "\n".join(f"{key}={payload_fields[key]}" for key in sorted(payload_fields))
    secret = hashlib.sha256(settings.bot_token.encode()).digest()
    signature = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    return signature


def _build_request(**kwargs):
    auth_date = kwargs.get("auth_date") or int(datetime.now(timezone.utc).timestamp())
    data = {
        "telegram_user_id": "123456",
        "auth_date": auth_date,
        "hash": _sign_payload(
            telegram_user_id="123456",
            auth_date=auth_date,
            first_name=kwargs.get("first_name"),
            last_name=kwargs.get("last_name"),
            username=kwargs.get("username"),
            photo_url=kwargs.get("photo_url"),
        ),
        "first_name": kwargs.get("first_name"),
        "last_name": kwargs.get("last_name"),
        "username": kwargs.get("username"),
        "photo_url": kwargs.get("photo_url"),
    }
    return TelegramAuthRequest(**{k: v for k, v in data.items() if v is not None})


def test_verify_telegram_login_accepts_valid_signature():
    request = _build_request(
        first_name="Alice",
        last_name="Agent",
        username="alice",
    )
    _verify_telegram_login(request)


def test_verify_telegram_login_rejects_invalid_hash():
    request = _build_request()
    request.hash = "bad-hash"
    with pytest.raises(HTTPException):
        _verify_telegram_login(request)


def test_verify_telegram_login_rejects_stale_data():
    past = int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp())
    request = _build_request(auth_date=past)
    with pytest.raises(HTTPException):
        _verify_telegram_login(request)
