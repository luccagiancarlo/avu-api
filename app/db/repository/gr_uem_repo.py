"""Repositório do GrUem — persistência em fin.gr_uem_regi.

Equivalente a `Gr_uemDAO.java` (incluir / informarRegistro / incluirPix).

Notas de portabilidade:
- O legado calcula `cd_gr` com `SELECT MAX(cd_gr)+1 FROM fin.gr_uem_regi` em
  camada de aplicação (sem SEQUENCE/IDENTITY). Replicamos aqui dentro da mesma
  transação para reduzir a janela de race — não elimina o problema, mas é o que
  temos enquanto o schema não muda. Veja PRD §12 item 10.
- `nu_convenio` fixo em 1410377 (perfil UEM).
- Datas: vencimento e boleto = hoje (mesmo comportamento do Java).
- Endereço vai com placeholders `-` quando o cliente não passa (idem legado).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GrUem

NU_CONVENIO_UEM = 1_410_377


async def proximo_cd_gr(session: AsyncSession) -> int:
    """`SELECT COALESCE(MAX(cd_gr), 0) + 1 FROM fin.gr_uem_regi`."""
    result = await session.execute(select(func.coalesce(func.max(GrUem.cd_gr), 0) + 1))
    return int(result.scalar_one())


async def existe_gr(
    session: AsyncSession,
    *,
    cd_recolhimento: int,
    cd_evento: int,
    nu_inscricao: int,
) -> int | None:
    """Equivale ao SELECT de existência em `Gr_uem_sgvDAO.java:143`."""
    stmt = select(GrUem.cd_gr).where(
        GrUem.cd_recolhimento == cd_recolhimento,
        GrUem.cd_evento == cd_evento,
        GrUem.nu_inscricao == nu_inscricao,
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return int(row) if row is not None else None


async def inserir_gr(
    session: AsyncSession,
    *,
    cd_recolhimento: int,
    cd_evento: int,
    nu_inscricao: int,
    nu_cpf: str,
    nm_nome: str,
    vl_boleto: Decimal,
    lt_pix: str,
    lt_pix_txid: str,
    en_logradouro: str = "-",
    en_bairro: str = "-",
    en_cidade: str = "-",
    en_estado: str = "-",
    en_cep: str = "-",
) -> int:
    """Insere GR e retorna `cd_gr` gerado.

    O caller é responsável por commit/rollback (atomicidade ponta-a-ponta).
    """
    hoje = date.today()
    gr = GrUem(
        cd_gr=await proximo_cd_gr(session),
        cd_recolhimento=cd_recolhimento,
        dt_vencimento=hoje,
        dt_boleto=hoje,
        nu_convenio=NU_CONVENIO_UEM,
        cd_evento=cd_evento,
        nu_inscricao=nu_inscricao,
        nu_cpf=nu_cpf.strip(),
        nm_nome=nm_nome,
        en_logradouro=en_logradouro,
        en_bairro=en_bairro,
        en_cidade=en_cidade,
        en_estado=en_estado,
        en_cep=en_cep,
        vl_boleto=vl_boleto,
        cd_solicitacao=0,
        cd_fatura=0,
        nu_ano=hoje.year,
        nu_remessa=0,
        st_remessa="N",
        lt_pix=lt_pix,
        lt_pix_txid=lt_pix_txid,
    )
    session.add(gr)
    await session.flush()
    return gr.cd_gr
