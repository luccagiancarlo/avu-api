from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: Literal["dev", "prod"] = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"

    # JWT
    jwt_secret: str
    jwt_alg: str = "HS512"
    jwt_expire_minutes: int = 480

    # DB2
    db2_host: str
    db2_port: int = 50000
    db2_database: str
    db2_user: str
    db2_password: str
    db2_pool_size: int = 10

    # BB UEM
    bb_uem_oauth_url: str
    bb_uem_cob_url: str
    bb_uem_client_id: str
    bb_uem_client_secret: str
    bb_uem_gw_app_key: str
    bb_uem_p12_path: Path
    bb_uem_p12_password: str
    bb_uem_cer_path: Path

    # Timeouts
    bb_connect_timeout_sec: int = 30
    bb_read_timeout_sec: int = 60

    # PIX
    pix_poll_interval_sec: int = 5
    pix_expiration_minutes: int = 5

    @property
    def db2_dsn(self) -> str:
        return (
            f"ibm_db_sa://{self.db2_user}:{self.db2_password}"
            f"@{self.db2_host}:{self.db2_port}/{self.db2_database}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
