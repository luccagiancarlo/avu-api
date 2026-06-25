"""Testes de autenticação nas rotas PIX."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _stub_env(monkeypatch):
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
    from app.settings import get_settings
    get_settings.cache_clear()


def _client():
    from app import main as main_mod
    return TestClient(main_mod.app)


def test_gruem_consulta_sem_token_retorna_401():
    r = _client().post("/gruem_consulta_pix", json={"txid": "abc"})
    assert r.status_code == 401


def test_gruem_consulta_token_invalido_retorna_401():
    r = _client().post(
        "/gruem_consulta_pix",
        json={"txid": "abc"},
        headers={"Authorization": "Bearer nao.eh.token"},
    )
    assert r.status_code == 401


def test_gruem_consulta_token_valido_passa_da_auth(monkeypatch):
    """Com token válido, a request passa do filtro de auth.

    Stub do cliente BB para não fazer chamada real.
    """
    from app.auth.jwt import create_token

    async def _fake_consultar(txid):
        return {"status": "ATIVA", "txid": txid}

    from app.bb import pix as pix_mod

    class _FakeClient:
        async def consultar_cobranca(self, txid):  # noqa: D401
            return await _fake_consultar(txid)

    monkeypatch.setattr(pix_mod, "get_uem_client", lambda: _FakeClient())
    from app.routers import gr_pix as gr_pix_mod
    monkeypatch.setattr(gr_pix_mod, "get_uem_client", lambda: _FakeClient())

    token = create_token(login="12345")
    r = _client().post(
        "/gruem_consulta_pix",
        json={"txid": "abc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ATIVA"


def test_webhook_publico_aceita_sem_token():
    r = _client().post("/gruem_webhook", json={"evento": "qualquer"})
    assert r.status_code == 200
    assert r.json() == {"received": True}
