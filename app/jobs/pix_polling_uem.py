"""Polling de status PIX UEM — substitui LoopConsultaPixPuroUEM.java.

Tick disparado pelo APScheduler (configurado em app/main.py).
NÃO usa while True — o scheduler controla a periodicidade via
`pix_poll_interval_sec`.

Para cada GR pendente:
  1. consulta status em api-pix.bb.com.br/pix/v2/cob/{txid}
  2. se CONCLUIDA → insere registro em fin.gr_retorno usando o horário
     real do pagamento que o BB devolve em `pix[0].horario`.

Divergência intencional do legado Java: o `LoopConsultaPixPuroUEM` usava
`dt_boleto` da própria GR como data de pagamento. Aqui usamos o horário
real do BB — mais correto para reconciliação financeira.

Erros transitórios (httpx, SQLAlchemy) são logados mas não derrubam o tick —
a próxima execução do scheduler reprocessa.
"""

from __future__ import annotations

import httpx
import structlog
from sqlalchemy.exc import SQLAlchemyError

from app.bb.parsing import extrair_pagamento
from app.bb.pix import get_uem_client
from app.db.repository.gr_retorno_repo import inserir_retorno, listar_pendentes
from app.db.session import AsyncSessionLocal

log = structlog.get_logger()

STATUS_PAGO = "CONCLUIDA"


async def run() -> None:
    async with AsyncSessionLocal() as session:
        try:
            pendentes = await listar_pendentes(session)
        except SQLAlchemyError as e:
            log.error("pix_poll_uem_listar_pendentes_falhou", err=str(e))
            return

        if not pendentes:
            log.debug("pix_poll_uem_sem_pendentes")
            return

        client = get_uem_client()
        for cd_gr, txid, _dt_boleto, vl_boleto in pendentes:
            try:
                cobranca = await client.consultar_cobranca(txid)
            except httpx.HTTPError as e:
                log.warning("pix_poll_uem_consulta_falhou", cd_gr=cd_gr, txid=txid, err=str(e))
                continue

            status = cobranca.get("status", "")
            if status != STATUS_PAGO:
                log.debug("pix_poll_uem_nao_pago", cd_gr=cd_gr, status=status)
                continue

            pagamento = extrair_pagamento(cobranca)
            if pagamento is None:
                # BB diz CONCLUIDA mas não trouxe o pix[]. Loga e pula —
                # próximo tick tenta de novo (idempotente).
                log.warning("pix_poll_uem_concluida_sem_pix", cd_gr=cd_gr, txid=txid)
                continue
            dt_pag, vl_pago = pagamento

            # Sanity check: valor do pagamento bate com o valor da GR.
            # Discrepância é apenas warning — o BB é a fonte da verdade.
            if vl_pago != vl_boleto:
                log.warning(
                    "pix_poll_uem_valor_divergente",
                    cd_gr=cd_gr,
                    vl_boleto=str(vl_boleto),
                    vl_pago=str(vl_pago),
                )

            try:
                inserido = await inserir_retorno(
                    session,
                    cd_gr=cd_gr,
                    dt_pag=dt_pag,
                    vl_pago=vl_pago,
                )
                await session.commit()
                if inserido:
                    log.info(
                        "pix_poll_uem_pago",
                        cd_gr=cd_gr,
                        txid=txid,
                        dt_pag=dt_pag.isoformat(),
                        vl=str(vl_pago),
                    )
            except SQLAlchemyError as e:
                await session.rollback()
                log.error("pix_poll_uem_inserir_retorno_falhou", cd_gr=cd_gr, err=str(e))
