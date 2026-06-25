"""Testes do repositório gr_retorno em SQLite (mesma técnica do test_gr_uem_repo)."""

from __future__ import annotations

from datetime import date, timedelta
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
    dt_vencimento: Mapped[date] = mapped_column(Date)
    dt_boleto: Mapped[date] = mapped_column(Date)
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


class _GrRetorno(_Base):
    __tablename__ = "gr_retorno"

    cd_gr: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dt_arquivo: Mapped[date] = mapped_column(Date)
    cd_sequencial: Mapped[str] = mapped_column(String(10))
    dt_pag: Mapped[date] = mapped_column(Date)
    dt_cre: Mapped[date] = mapped_column(Date)
    vl_gr: Mapped[float] = mapped_column(Numeric(10, 2))
    vl_tarifa: Mapped[float] = mapped_column(Numeric(10, 2))
    vl_multa: Mapped[float] = mapped_column(Numeric(10, 2))
    vl_recebido: Mapped[float] = mapped_column(Numeric(10, 2))
    vl_desconto: Mapped[float] = mapped_column(Numeric(10, 2))
    nm_arquivo: Mapped[str] = mapped_column(String(50))


@pytest.fixture
async def session(monkeypatch):
    from app.db.repository import gr_retorno_repo

    monkeypatch.setattr(gr_retorno_repo, "GrUem", _GrUem)
    monkeypatch.setattr(gr_retorno_repo, "GrRetorno", _GrRetorno)

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


def _fake_gr(cd_gr: int, *, txid: str | None = "abc", boleto: date | None = None) -> _GrUem:
    return _GrUem(
        cd_gr=cd_gr,
        cd_recolhimento=1,
        dt_vencimento=date.today(),
        dt_boleto=boleto or date.today(),
        nu_convenio=1_410_377,
        cd_evento=0,
        nu_inscricao=0,
        nu_cpf="",
        nm_nome="x",
        en_logradouro="-",
        en_bairro="-",
        en_cidade="-",
        en_estado="-",
        en_cep="-",
        vl_boleto=Decimal("10.00"),
        cd_solicitacao=0,
        cd_fatura=0,
        nu_ano=date.today().year,
        nu_remessa=0,
        st_remessa="N",
        lt_pix="00020...",
        lt_pix_txid=txid,
        lt_digitavel=None,
    )


async def test_listar_pendentes_inclui_gr_com_txid_e_sem_retorno(session):
    from app.db.repository.gr_retorno_repo import listar_pendentes

    session.add(_fake_gr(1))
    session.add(_fake_gr(2, txid=None))  # sem txid → não retorna
    await session.commit()

    rows = await listar_pendentes(session)
    assert [r[0] for r in rows] == [1]


async def test_listar_pendentes_exclui_gr_ja_retornados(session):
    from app.db.repository.gr_retorno_repo import inserir_retorno, listar_pendentes

    session.add(_fake_gr(1))
    await session.commit()
    await inserir_retorno(session, cd_gr=1, dt_pag=date.today(), vl_pago=Decimal("10.00"))
    await session.commit()

    rows = await listar_pendentes(session)
    assert rows == []


async def test_listar_pendentes_exclui_boleto_vencido(session):
    from app.db.repository.gr_retorno_repo import listar_pendentes

    session.add(_fake_gr(1, boleto=date.today() - timedelta(days=1)))
    await session.commit()

    rows = await listar_pendentes(session)
    assert rows == []


async def test_inserir_retorno_idempotente(session):
    from app.db.repository.gr_retorno_repo import inserir_retorno

    session.add(_fake_gr(1))
    await session.commit()

    primeira = await inserir_retorno(session, cd_gr=1, dt_pag=date.today(), vl_pago=Decimal("10.00"))
    await session.commit()
    segunda = await inserir_retorno(session, cd_gr=1, dt_pag=date.today(), vl_pago=Decimal("10.00"))
    await session.commit()

    assert primeira is True
    assert segunda is False


async def test_inserir_retorno_calcula_dt_cre_d_mais_1(session):
    from app.db.repository.gr_retorno_repo import inserir_retorno
    from app.db.models import GrRetorno  # noqa: F401 — registrar metadata
    from sqlalchemy import select

    session.add(_fake_gr(1))
    await session.commit()

    hoje = date(2026, 6, 24)
    await inserir_retorno(session, cd_gr=1, dt_pag=hoje, vl_pago=Decimal("10.00"))
    await session.commit()

    row = (await session.execute(select(_GrRetorno).where(_GrRetorno.cd_gr == 1))).scalar_one()
    assert row.dt_pag == hoje
    assert row.dt_cre == hoje + timedelta(days=1)
    assert Decimal(str(row.vl_tarifa)) == Decimal("0.93")
    assert row.nm_arquivo == "Webhook PIX"
