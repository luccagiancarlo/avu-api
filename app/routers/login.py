"""Rota POST /login — equivalente a LoginResource.fazerLogin do legado.

Escopo Fase 3 inicial: validar credenciais + emitir JWT + devolver dados
mínimos do candidato. Enriquecimentos (curso, sala, etapa, coringas, status
de pagamento) ficam para uma fase posterior junto com /dados_alunos_rh.

O comportamento "esqueceu_a_senha" do legado dispara envio de email com a
senha em texto puro (PRD §12 marca como falha grave). Aqui mantemos a
funcionalidade mas com TODO claro para substituir por fluxo de reset por
token. O envio em si é stub até portarmos o serviço de email.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_token
from app.db.repository.candidato_repo import (
    autenticar,
    buscar_email_para_recuperacao,
)
from app.db.session import get_session

log = structlog.get_logger()
router = APIRouter(tags=["auth"])

SENHA_RESET_FLAG = "esqueceu_a_senha"


class Credenciais(BaseModel):
    nu_inscricao: str
    de_senha: str
    lt_token_not: str | None = None  # token Firebase do dispositivo (opcional)


class LoginResponse(BaseModel):
    token: str
    nu_inscricao: int
    dv_inscricao: int
    nm_candidato: str
    nu_cpf: str
    tp_evento: str  # "VE" ou "PA"


@router.post("/login", response_model=LoginResponse)
async def fazer_login(
    cred: Credenciais,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    """Valida credenciais e emite JWT."""
    if cred.de_senha == SENHA_RESET_FLAG:
        # Caminho "esqueceu a senha": dispara email e bloqueia login.
        # O legado seguia tentando autenticar com essa flag como senha — comportamento
        # inútil, sempre falhava no SELECT. Aqui retornamos 200 com mensagem clara.
        await _disparar_recuperacao(session, cred.nu_inscricao)
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="email de recuperação enviado",
        )

    candidato = await autenticar(
        session,
        inscr_completa=cred.nu_inscricao,
        senha=cred.de_senha,
    )
    if candidato is None:
        log.info("login_falhou", inscr=cred.nu_inscricao)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "credenciais inválidas")

    token = create_token(login=cred.nu_inscricao)
    log.info("login_ok", inscr=cred.nu_inscricao, tp_evento=candidato.tp_evento)

    # TODO Fase 3.5: persistir `lt_token_not` em sgv.sgv_dispcand
    # (CandidatoDAO.registrarToken — usado para push Firebase).
    return LoginResponse(
        token=token,
        nu_inscricao=candidato.nu_inscricao,
        dv_inscricao=candidato.dv_inscricao,
        nm_candidato=candidato.nm_candidato,
        nu_cpf=candidato.nu_cpf,
        tp_evento=candidato.tp_evento,
    )


async def _disparar_recuperacao(session: AsyncSession, inscr_completa: str) -> None:
    """Stub de envio de email com a senha. TODO: substituir por reset por token."""
    dados = await buscar_email_para_recuperacao(session, inscr_completa=inscr_completa)
    if dados is None:
        # Não vazamos se a inscrição existe ou não.
        log.info("recuperacao_inscr_inexistente", inscr=inscr_completa)
        return
    nm, email, _senha = dados
    log.info("recuperacao_email_pendente", inscr=inscr_completa, email=email, nm=nm)
    # TODO: chamar serviço de email (a portar)
