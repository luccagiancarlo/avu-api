"""Testes do router /login.

Mocka `autenticar` e `buscar_email_para_recuperacao` para não depender de DB2.
"""

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


def _client_com_mocks(autenticar_retorno=None, email_retorno=None):
    """Cria TestClient com get_session noop e mocks injetados no router."""
    from app import main as main_mod
    from app.db.repository import candidato_repo
    from app.db.session import get_session

    async def _noop_session():
        yield None

    main_mod.app.dependency_overrides[get_session] = _noop_session

    async def _fake_autenticar(session, *, inscr_completa, senha):
        return autenticar_retorno

    async def _fake_email(session, *, inscr_completa):
        return email_retorno

    candidato_repo.autenticar = _fake_autenticar  # type: ignore[assignment]
    candidato_repo.buscar_email_para_recuperacao = _fake_email  # type: ignore[assignment]
    # router importa as funções por referência — patch precisa atingir o módulo do router também
    from app.routers import login as login_router
    login_router.autenticar = _fake_autenticar  # type: ignore[assignment]
    login_router.buscar_email_para_recuperacao = _fake_email  # type: ignore[assignment]

    return TestClient(main_mod.app)


def test_login_credenciais_validas_retorna_token():
    from app.db.repository.candidato_repo import CandidatoAutenticado

    candidato = CandidatoAutenticado(
        nu_inscricao=12345,
        dv_inscricao=6,
        nm_candidato="FULANO DA SILVA",
        nu_cpf="12345678900",
        tp_evento="VE",
    )
    client = _client_com_mocks(autenticar_retorno=candidato)

    r = client.post("/login", json={"nu_inscricao": "123456", "de_senha": "abcd1234"})
    assert r.status_code == 200
    body = r.json()
    assert body["nu_inscricao"] == 12345
    assert body["nm_candidato"] == "FULANO DA SILVA"
    assert body["tp_evento"] == "VE"
    assert body["token"].count(".") == 2  # JWT tem 3 partes


def test_login_credenciais_invalidas_retorna_401():
    client = _client_com_mocks(autenticar_retorno=None)
    r = client.post("/login", json={"nu_inscricao": "123456", "de_senha": "errada"})
    assert r.status_code == 401


def test_login_esqueceu_a_senha_retorna_202():
    client = _client_com_mocks(email_retorno=("FULANO", "x@y", "senha123"))
    r = client.post("/login", json={"nu_inscricao": "123456", "de_senha": "esqueceu_a_senha"})
    assert r.status_code == 202


def test_login_esqueceu_a_senha_inscr_inexistente_tambem_retorna_202():
    """Não vaza se a inscrição existe ou não."""
    client = _client_com_mocks(email_retorno=None)
    r = client.post("/login", json={"nu_inscricao": "999999", "de_senha": "esqueceu_a_senha"})
    assert r.status_code == 202
