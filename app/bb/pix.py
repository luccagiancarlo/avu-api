"""Factory dos clientes BB. Mantém instância singleton via lru_cache."""

from __future__ import annotations

from functools import lru_cache

from app.bb.client import BBPixClient
from app.bb.oauth import OAuthClient
from app.settings import get_settings


@lru_cache
def get_uem_client() -> BBPixClient:
    s = get_settings()
    oauth = OAuthClient(
        token_url=s.bb_uem_oauth_url,
        client_id=s.bb_uem_client_id,
        client_secret=s.bb_uem_client_secret,
        connect_timeout=s.bb_connect_timeout_sec,
        read_timeout=s.bb_read_timeout_sec,
    )
    return BBPixClient(
        profile="UEM",
        cob_url=s.bb_uem_cob_url,
        gw_app_key=s.bb_uem_gw_app_key,
        oauth=oauth,
        p12_path=str(s.bb_uem_p12_path),
        p12_password=s.bb_uem_p12_password,
        connect_timeout=s.bb_connect_timeout_sec,
        read_timeout=s.bb_read_timeout_sec,
    )
