"""Rotas PIX UEM — equivalente FastAPI de PixResource.java.

Divergência intencional do legado: `PixResource.java` não usa `@Seguro` (rota
aberta em produção). Aqui exigimos JWT (`require_token`) em todas as
operações. Clientes legados precisam autenticar primeiro em `/login` e enviar
`Authorization: Bearer <token>`.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from app.auth.jwt import require_token
from app.bb.pix import get_uem_client
from app.db.repository.gr_uem_repo import inserir_gr
from app.db.session import get_session

log = structlog.get_logger()

# Router padrão exige JWT — usado para todas as rotas chamadas por clientes UEM.
router = APIRouter(tags=["pix"], dependencies=[Depends(require_token)])

# Webhook é chamado pelo próprio BB, sem token nosso. Mantemos público mas
# isso deve ser substituído por validação de assinatura BB / IP allowlist
# em Fase 2 quando portarmos o webhook real. Ver TODO no handler.
public_router = APIRouter(tags=["pix-webhook"])


# ---------------- DTOs (espelham os do legado para compatibilidade) ----------------

class Calendario(BaseModel):
    expiracao: int = 3600


class Devedor(BaseModel):
    cpf: str = ""
    cnpj: str = ""
    nome: str


class Valor(BaseModel):
    original: str


class DadosPixChamada(BaseModel):
    calendario: Calendario = Field(default_factory=Calendario)
    devedor: Devedor
    valor: Valor
    chave: str
    solcnpjitacaoPagador: str = ""
    cd_recolhimento: str
    ra_ou_matricula_ou_inscricao: str = ""
    cd_evento: str = "0"


class RespostaPix(BaseModel):
    pix: str
    txid: str
    cd_gr: int


# ---------------- helpers ----------------

def _to_dados_pix(dpc: DadosPixChamada) -> dict:
    return {
        "calendario": dpc.calendario.model_dump(),
        "devedor": dpc.devedor.model_dump(),
        "valor": dpc.valor.model_dump(),
        "chave": dpc.chave,
        "solcnpjitacaoPagador": dpc.solcnpjitacaoPagador,
    }


def _to_decimal(valor: str) -> Decimal:
    try:
        return Decimal(valor.replace(",", "."))
    except (InvalidOperation, AttributeError) as e:
        raise HTTPException(status_code=400, detail=f"valor.original inválido: {valor!r}") from e


def _to_int_safe(s: str) -> int:
    try:
        return int(s) if s else 0
    except ValueError:
        return 0


# ---------------- endpoints ----------------

@router.post("/gruem_pix", response_model=RespostaPix)
async def criar_pix_uem(
    dpc: DadosPixChamada,
    session: AsyncSession = Depends(get_session),
) -> RespostaPix:
    """Equivalente a `POST /avu/rest/gruem_pix` (PixResource.java)."""
    # 1) BB criar cobrança
    client = get_uem_client()
    try:
        retorno = await client.criar_cobranca(_to_dados_pix(dpc))
    except Exception as e:
        log.error("bb_criar_cob_falhou", err=str(e))
        raise HTTPException(status_code=502, detail=f"BB criar cob falhou: {e}") from e

    lt_pix = retorno["pixCopiaECola"]
    lt_pix_txid = retorno["txid"]

    # 2) Persistir GrUem em fin.gr_uem_regi
    # Retry equivale ao loop de 10x do legado (PixResource.java:307-328), porém
    # só em erros transitórios de banco. Mantemos a janela curta para não
    # bloquear a request por muito tempo.
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(5),
            wait=wait_fixed(0.5),
            retry=retry_if_exception_type(SQLAlchemyError),
            reraise=True,
        ):
            with attempt:
                cd_gr = await inserir_gr(
                    session,
                    cd_recolhimento=_to_int_safe(dpc.cd_recolhimento),
                    cd_evento=_to_int_safe(dpc.cd_evento),
                    nu_inscricao=_to_int_safe(dpc.ra_ou_matricula_ou_inscricao),
                    nu_cpf=dpc.devedor.cnpj or dpc.devedor.cpf,
                    nm_nome=dpc.devedor.nome,
                    vl_boleto=_to_decimal(dpc.valor.original),
                    lt_pix=lt_pix,
                    lt_pix_txid=lt_pix_txid,
                )
                await session.commit()
    except (RetryError, SQLAlchemyError) as e:
        await session.rollback()
        log.error("gr_insert_falhou_apos_retries", err=str(e), txid=lt_pix_txid)
        # PIX foi criado no BB mas não persistido — devolvemos 502 com o txid
        # para o cliente reconciliar manualmente.
        raise HTTPException(
            status_code=502,
            detail=f"PIX criado (txid={lt_pix_txid}) mas falha ao gravar GR",
        ) from e

    log.info("gr_uem_inserida", cd_gr=cd_gr, txid=lt_pix_txid)
    return RespostaPix(pix=lt_pix, txid=lt_pix_txid, cd_gr=cd_gr)


@router.post("/gruem_consulta_pix")
async def consultar_pix_uem(payload: dict) -> dict:
    txid = payload.get("txid")
    if not txid:
        raise HTTPException(status_code=400, detail="txid obrigatório")
    return await get_uem_client().consultar_cobranca(txid)


@public_router.post("/gruem_webhook")
async def webhook_uem(payload: dict) -> dict:
    # TODO Fase 2: gravar em sgv.sgv_gr_webhook + INSERT em fin.gr_retorno
    # TODO Segurança: validar origem (assinatura HMAC do BB ou allowlist de IP).
    return {"received": True}
