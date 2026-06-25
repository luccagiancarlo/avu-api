"""Cliente BB PIX (criar e consultar cobrança) com mTLS."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.bb.certificates import build_ssl_context
from app.bb.oauth import OAuthClient

log = structlog.get_logger()


class BBPixClient:
    def __init__(
        self,
        profile: str,
        cob_url: str,
        gw_app_key: str,
        oauth: OAuthClient,
        p12_path: str,
        p12_password: str,
        connect_timeout: int = 30,
        read_timeout: int = 60,
    ) -> None:
        self.profile = profile
        self.cob_url = cob_url
        self.gw_app_key = gw_app_key
        self.oauth = oauth
        self._ssl = build_ssl_context(p12_path, p12_password)
        self._timeout = httpx.Timeout(connect=connect_timeout, read=read_timeout, write=read_timeout, pool=connect_timeout)

    def _params(self) -> dict[str, str]:
        return {"gw-dev-app-key": self.gw_app_key}

    async def criar_cobranca(self, dados_pix: dict[str, Any]) -> dict[str, Any]:
        token = await self.oauth.token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(verify=self._ssl, timeout=self._timeout) as client:
            resp = await client.post(
                self.cob_url,
                headers=headers,
                params=self._params(),
                json=dados_pix,
            )
            log.info("bb_criar_cob", profile=self.profile, status=resp.status_code)
            resp.raise_for_status()
            return resp.json()

    async def consultar_cobranca(self, txid: str) -> dict[str, Any]:
        token = await self.oauth.token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.cob_url}/{txid}"
        async with httpx.AsyncClient(verify=self._ssl, timeout=self._timeout) as client:
            resp = await client.get(url, headers=headers, params=self._params())
            log.info("bb_consultar_cob", profile=self.profile, txid=txid, status=resp.status_code)
            resp.raise_for_status()
            return resp.json()
