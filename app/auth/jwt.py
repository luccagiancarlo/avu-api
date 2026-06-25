"""JWT HS512 compatível com FiltroAutenticacao do legado Java.

Compat detalhada com o `LoginResource.gerarToken` Java:

1. Chave HMAC: o Java faz `DatatypeConverter.parseBase64Binary(secret)`. Replicamos
   isso decodificando o segredo como base64 — se decode falhar, caímos no UTF-8
   bruto (mesmo comportamento permissivo do Java).
2. Claim do login: o Java usa `.setIssuer(login)`, que grava em `iss`. O filtro
   tenta ler com `claims.getId()` (que retorna `jti`) — bug no legado: o login
   nunca era recuperado. Aqui usamos `iss` corretamente e expomos `get_login()`
   como helper.
3. Expiração: o Java usa `Calendar.add(DAY_OF_MONTH, expiraEmDias)`. Mantemos em
   minutos via `JWT_EXPIRE_MINUTES` (default 480 = 8h).
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.settings import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)


def _hmac_key() -> bytes:
    """Decodifica o JWT_SECRET como base64, fallback para UTF-8 bruto.

    Reproduz `DatatypeConverter.parseBase64Binary(secret)` do Java.
    """
    secret = get_settings().jwt_secret
    try:
        # base64.b64decode é permissivo se houver chars inválidos? Não — mas
        # urlsafe_b64decode também não. Usamos b64decode com validate=False
        # para não estourar; se vier algo realmente impossível, caímos no UTF-8.
        return base64.b64decode(secret + "==", validate=False)
    except Exception:
        return secret.encode("utf-8")


def create_token(login: str) -> str:
    """Gera JWT com `iss=login` (compat com LoginResource.java)."""
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "iss": login,
        "iat": now,
        "exp": now + timedelta(minutes=s.jwt_expire_minutes),
    }
    return jwt.encode(payload, _hmac_key(), algorithm=s.jwt_alg)


def decode_token(token: str) -> dict:
    s = get_settings()
    try:
        # `options={"verify_iss": False}` porque o `iss` carrega o login, não o
        # emissor real — não há valor único para comparar.
        return jwt.decode(token, _hmac_key(), algorithms=[s.jwt_alg], options={"verify_iss": False})
    except JWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from e


def get_login(claims: dict) -> str:
    """Extrai o login do payload (claim `iss`)."""
    login = claims.get("iss")
    if not login:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token sem login")
    return str(login)


def require_token(token: str | None = Depends(oauth2_scheme)) -> dict:
    """Dependência FastAPI equivalente a `@Seguro` do JAX-RS."""
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    return decode_token(token)
