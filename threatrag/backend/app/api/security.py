"""Shared-secret API key guard. Off when API_KEY is empty (local dev).

Interim control until OIDC/JWT lands (spec/phase4.md Part B).
"""
import secrets

from fastapi import Header, HTTPException

from app.core.config import get_settings


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = get_settings().api_key
    if not expected:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key")
