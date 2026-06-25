from datetime import date

from sqlalchemy import BigInteger, Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class GrUem(Base):
    """fin.gr_uem_regi — GR/PIX do perfil UEM (nu_convenio=1410377)."""

    __tablename__ = "gr_uem_regi"
    __table_args__ = {"schema": "fin"}

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
    cd_solicitacao: Mapped[int] = mapped_column(BigInteger, default=0)
    cd_fatura: Mapped[int] = mapped_column(BigInteger, default=0)
    nu_ano: Mapped[int] = mapped_column(BigInteger)
    nu_remessa: Mapped[int] = mapped_column(BigInteger, default=0)
    st_remessa: Mapped[str] = mapped_column(String(1), default="N")
    lt_pix: Mapped[str | None] = mapped_column(String, nullable=True)
    lt_pix_txid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lt_digitavel: Mapped[str | None] = mapped_column(String, nullable=True)
