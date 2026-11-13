"""Who is calling, and how often.

With JWT_SECRET set, every /api/v1 call needs `Authorization: Bearer <HS256 token>` and the
caller is its `sub` claim. Without it (local development) every caller is "anonymous".
Chat sessions are stored under the caller, so one identity cannot read another's history.
"""
import time

import jwt
from fastapi import Depends, Header, HTTPException, Request
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.state import get_state

ANONYMOUS = "anonymous"
_WINDOW_S = 60


class Identity(BaseModel):
    sub: str
    authenticated: bool = False


async def current_identity(authorization: str | None = Header(default=None)) -> Identity:
    secret = get_settings().jwt_secret
    if not secret:
        return Identity(sub=ANONYMOUS)
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Missing bearer token", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["sub", "exp"]})
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}", headers={"WWW-Authenticate": "Bearer"}) from exc
    return Identity(sub=str(claims["sub"]), authenticated=True)


async def rate_limit(request: Request, identity: Identity = Depends(current_identity)) -> None:
    """Fixed one-minute window per identity, or per client address when anonymous."""
    limit = get_settings().rate_limit_per_minute
    if limit <= 0:
        return
    who = identity.sub if identity.authenticated else f"ip:{request.client.host if request.client else 'unknown'}"
    window = int(time.time() // _WINDOW_S)
    count = await get_state().incr(f"rl:{who}:{window}", ttl_s=_WINDOW_S * 2)
    if count > limit:
        retry = _WINDOW_S - int(time.time() % _WINDOW_S)
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": str(retry)})


async def llm_budget() -> None:
    """Global daily ceiling on requests that call a model, for a public demo: bounds spend no
    matter how many visitors or addresses there are. Counts attempts, not tokens."""
    cap = get_settings().llm_daily_request_cap
    if cap <= 0:
        return
    day = time.strftime("%Y-%m-%d", time.gmtime())
    if await get_state().incr(f"llm-budget:{day}", ttl_s=2 * 86400) > cap:
        retry = 86400 - int(time.time() % 86400)
        raise HTTPException(status_code=429, detail="Daily model budget for this demo is used up; try again tomorrow",
                            headers={"Retry-After": str(retry)})


def mint_token(sub: str, hours: float = 8.0) -> str:
    secret = get_settings().jwt_secret
    if not secret:
        raise RuntimeError("JWT_SECRET is not set")
    return jwt.encode({"sub": sub, "exp": int(time.time() + hours * 3600)}, secret, algorithm="HS256")
