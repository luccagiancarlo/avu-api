"""Testes do módulo app/auth/jwt.py (compat com legado Java)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def _stub_settings(monkeypatch):
    for k, v in {
        "JWT_SECRET": "oSenhorEhMeuPastor",
        "JWT_ALG": "HS512",
        "JWT_EXPIRE_MINUTES": "60",
        "DB2_HOST": "x",
        "DB2_DATABASE": "x",
        "DB2_USER": "x",
        "DB2_PASSWORD": "x",
        "BB_UEM_OAUTH_URL": "https://x",
        "BB_UEM_COB_URL": "https://x",
        "BB_UEM_CLIENT_ID": "x",
        "BB_UEM_CLIENT_SECRET": "x",
        "BB_UEM_GW_APP_KEY": "x",
        "BB_UEM_P12_PATH": "/tmp/x.p12",
        "BB_UEM_P12_PASSWORD": "x",
        "BB_UEM_CER_PATH": "/tmp/x.cer",
    }.items():
        monkeypatch.setenv(k, v)
    # Limpa cache do get_settings entre testes
    from app.settings import get_settings
    get_settings.cache_clear()


def test_round_trip_iss_carrega_login():
    from app.auth.jwt import create_token, decode_token, get_login

    token = create_token(login="12345")
    claims = decode_token(token)
    assert get_login(claims) == "12345"
    assert "iat" in claims and "exp" in claims


def test_decode_token_invalido_levanta_401():
    from app.auth.jwt import decode_token

    with pytest.raises(HTTPException) as exc:
        decode_token("nao.eh.token")
    assert exc.value.status_code == 401


def test_get_login_sem_iss_levanta_401():
    from app.auth.jwt import get_login

    with pytest.raises(HTTPException) as exc:
        get_login({"foo": "bar"})
    assert exc.value.status_code == 401
