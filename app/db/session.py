from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.settings import get_settings

_settings = get_settings()

# ibm-db-sa não tem driver async nativo. Usamos `create_async_engine` em
# modo "wrap sync" — a SQLAlchemy delega para um pool sync. Para tirar
# proveito real de async, considerar driver alternativo no futuro.
engine = create_async_engine(
    _settings.db2_dsn.replace("ibm_db_sa://", "ibm_db_sa+ibm_db://"),
    pool_size=_settings.db2_pool_size,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
