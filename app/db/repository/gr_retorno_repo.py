"""Repositório de retornos de pagamento — fin.gr_retorno.

Equivale a `LoopConsultaPixPuroUEM.java` (SELECT pendentes + INSERT retorno).

Divergências intencionais do legado:
- `dt_pag` = horário real do BB (`pix[0].horario`), não `dt_boleto` da GR como
  no Java. O legado registrava a data de emissão como data de pagamento, o
  que perdia a data real de quitação.

Detalhes do legado preservados:
- `VL_TARIFA = 0.93` hardcoded. PRD §12 item 9 marca para parametrizar.
- `CD_SEQUENCIAL = '0'` (legado também usa string '0').
- `DT_CRE = DT_PAG + 1 dia` (replica `zk.data1DiaDepois`).
- Idempotência via `WHERE cd_gr` antes de inserir.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GrRetorno, GrUem

VL_TARIFA_PIX_BB = Decimal("0.93")  # TODO: ler do response BB quando disponível
NM_ARQUIVO_WEBHOOK = "Webhook PIX"


async def listar_pendentes(session: AsyncSession) -> Sequence[tuple[int, str, date, Decimal]]:
    """`SELECT cd_gr, lt_pix_txid, dt_boleto, vl_boleto FROM fin.gr_uem_regi a
        WHERE a.lt_pix_txid IS NOT NULL
          AND a.dt_boleto >= current_date
          AND a.cd_gr NOT IN (SELECT cd_gr FROM fin.gr_retorno b WHERE b.cd_gr = a.cd_gr)`

    Retorna lista de tuplas (cd_gr, txid, dt_boleto, vl_boleto).
    """
    subq = select(GrRetorno.cd_gr)
    stmt = (
        select(GrUem.cd_gr, GrUem.lt_pix_txid, GrUem.dt_boleto, GrUem.vl_boleto)
        .where(
            GrUem.lt_pix_txid.is_not(None),
            GrUem.dt_boleto >= date.today(),
            GrUem.cd_gr.not_in(subq),
        )
    )
    result = await session.execute(stmt)
    return result.all()  # type: ignore[return-value]


async def ja_tem_retorno(session: AsyncSession, cd_gr: int) -> bool:
    result = await session.execute(
        select(func.count(GrRetorno.cd_gr)).where(GrRetorno.cd_gr == cd_gr)
    )
    return int(result.scalar_one()) > 0


async def inserir_retorno(
    session: AsyncSession,
    *,
    cd_gr: int,
    dt_pag: date,
    vl_pago: Decimal,
) -> bool:
    """Insere retorno se ainda não existir. Retorna True se inseriu, False se já existia."""
    if await ja_tem_retorno(session, cd_gr):
        return False

    retorno = GrRetorno(
        cd_gr=cd_gr,
        dt_arquivo=dt_pag,
        cd_sequencial="0",
        dt_pag=dt_pag,
        dt_cre=dt_pag + timedelta(days=1),
        vl_gr=vl_pago,
        vl_tarifa=VL_TARIFA_PIX_BB,
        vl_multa=Decimal("0.00"),
        vl_recebido=vl_pago,
        vl_desconto=Decimal("0.00"),
        nm_arquivo=NM_ARQUIVO_WEBHOOK,
    )
    session.add(retorno)
    await session.flush()
    return True
