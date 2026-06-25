"""Testes unitários do repositório GrUem usando SQLite em memória.

Atenção: schemas DB2 (fin., sgv.) não existem no SQLite. Para o teste do
INSERT/MAX validamos a lógica do repo isolando-a numa cópia do model sem
schema (override via __table_args__).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, Date, Numeric, String
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class _Base(DeclarativeBase):
    pass


class _GrUem(_Base):
    __tablename__ = "gr_uem_regi"

    cd_gr: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cd_recolhimento: Mapped[int] = mapped_column(BigInteger)
    dt_vencimento: Mapped[object] = mapped_column(Date)
    dt_boleto: Mapped[object] = mapped_column(Date)
    nu_convenio: Mapped[int] = mapped_column(BigInteger)
    cd_evento: Mapped[int] = mapped_column(BigInteger)
    nu_inscricao: Mapped[int] = mapped_column(BigInteger)
    nu_cpf: Mapped[str] = mapped_column(String(20))
    nm_nome: Mapped[str] = mapped_column(String(200))
    en_logradouro: Mapped[str] = mapped_column(String(200))
    en_bairro: Mapped[str] = mapped_column(String(100))
    en_cidade: Mapped[str] = mapped_column(String(100))
    en_estado: Mapped[str] = mapped_column(String(2))
    en_cep: Mapped[str] = mapped_column(String(10))
    vl_boleto: Mapped[float] = mapped_column(Numeric(10, 2))
    cd_solicitacao: Mapped[int] = mapped_column(BigInteger)
    cd_fatura: Mapped[int] = mapped_column(BigInteger)
    nu_ano: Mapped[int] = mapped_column(BigInteger)
    nu_remessa: Mapped[int] = mapped_column(BigInteger)
    st_remessa: Mapped[str] = mapped_column(String(1))
    lt_pix: Mapped[str | None] = mapped_column(String, nullable=True)
    lt_pix_txid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lt_digitavel: Mapped[str | None] = mapped_column(String, nullable=True)


@pytest.fixture
async def session(monkeypatch):
    # patcha o model do repo para usar a versão sem schema
    from app.db.repository import gr_uem_repo

    monkeypatch.setattr(gr_uem_repo, "GrUem", _GrUem)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_proximo_cd_gr_em_tabela_vazia(session):
    from app.db.repository.gr_uem_repo import proximo_cd_gr

    assert await proximo_cd_gr(session) == 1


async def test_inserir_gr_basico(session):
    from app.db.repository.gr_uem_repo import inserir_gr, proximo_cd_gr

    cd_gr = await inserir_gr(
        session,
        cd_recolhimento=12345,
        cd_evento=0,
        nu_inscricao=98765,
        nu_cpf="12345678000190",
        nm_nome="TESTE",
        vl_boleto=Decimal("120.00"),
        lt_pix="00020126...",
        lt_pix_txid="abc-123",
    )
    await session.commit()
    assert cd_gr == 1
    assert await proximo_cd_gr(session) == 2
