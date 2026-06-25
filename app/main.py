from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import log, setup_logging
from app.jobs import pix_polling_uem
from app.routers import gr_pix, login
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.app_log_level)
    log.info("avu_api_starting", env=settings.app_env)

    scheduler = await _start_scheduler(settings)
    app.state.scheduler = scheduler

    try:
        yield
    finally:
        log.info("avu_api_shutting_down")
        scheduler.shutdown(wait=False)


async def _start_scheduler(settings):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        pix_polling_uem.run,
        "interval",
        seconds=settings.pix_poll_interval_sec,
        id="pix_poll_uem",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler


app = FastAPI(title="AVU API", version="0.1.0", lifespan=lifespan)
app.include_router(login.router)
app.include_router(gr_pix.router)
app.include_router(gr_pix.public_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
