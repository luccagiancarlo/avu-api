from datetime import date

from sqlalchemy import BigInteger, Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class GrRetorno(Base):
    """fin.gr_retorno — retorno de pagamento PIX/boleto do perfil UEM.

    Equivale ao INSERT em LoopConsultaPixPuroUEM.java:70-72. O legado não
    documenta PK formal — pelo uso (`WHERE CD_GR = :cd_gr` para checar
    idempotência) tratamos `cd_gr` como chave lógica de unicidade por GR.
    PK física aqui declarada como `cd_gr` para o ORM funcionar; ajustar
    se a tabela real tiver outra PK.
    """

    __tablename__ = "gr_retorno"
    __table_args__ = {"schema": "fin"}

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
