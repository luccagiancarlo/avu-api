"""OAuth2 client_credentials com cache de token em memória.

Tokens BB duram ~10 min. Cacheamos em memória e renovamos
preventivamente 30s antes da expiração.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass

import httpx
import structlog

log = structlog.get_logger()


@dataclass
class CachedToken:
    access_token: str
    expires_at: float  # epoch seconds


class OAuthClient:
    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str = "pix.arrecadacao-requisicao pix.arrecadacao-info",
        connect_timeout: int = 30,
        read_timeout: int = 60,
    ) -> None:
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self._cache: CachedToken | None = None
        self._timeout = httpx.Timeout(connect=connect_timeout, read=read_timeout, write=read_timeout, pool=connect_timeout)

    async def token(self, force_refresh: bool = False) -> str:
        now = time.time()
        if not force_refresh and self._cache and now < self._cache.expires_at - 30:
            return self._cache.access_token

        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic}",
            "Cache-Control": "no-cache",
        }
        body = f"grant_type=client_credentials&scope={self.scope.replace(' ', '%20')}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(self.token_url, headers=headers, content=body)
            resp.raise_for_status()
            data = resp.json()

        token = data["access_token"]
        expires_in = int(data.get("expires_in", 600))
        self._cache = CachedToken(access_token=token, expires_at=now + expires_in)
        log.info("bb_oauth_token_refreshed", expires_in=expires_in)
        return token
