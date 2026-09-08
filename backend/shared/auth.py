"""
################################################################################
# TEMPORARY STUB — OWNED BY M6, NOT M2.
#
# This file exists ONLY so M2's intake endpoints can import and test
# `require_role()` / `get_current_user()` before M6 pushes the real
# implementation (per the doc's "nobody blocks on someone else finishing —
# build against mocked data" rule).
#
# When M6's real shared/auth.py is ready, this will be updated to verify
# the actual Supabase JWT and look up `profiles` from the live Supabase
# Postgres connection.
################################################################################

Two modes, controlled by AUTH_DEV_MODE in .env:

  AUTH_DEV_MODE=true   -> bypasses real JWT verification entirely. Reads
                          X-Dev-User-Id / X-Dev-Role headers (or dev bearer token)
                          instead, so M2 can hit the API directly (e.g. via /docs or curl)
                          without a real Supabase login flow set up yet.

  AUTH_DEV_MODE=false  -> attempts real Supabase JWT verification using
                          SUPABASE_JWT_SECRET (HS256).
"""
import os
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException

AUTH_DEV_MODE = os.environ.get("AUTH_DEV_MODE", "true").lower() == "true"
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")


@dataclass
class CurrentUser:
    id: str          # profiles.id / auth.users.id, as a string UUID
    full_name: str
    role: str         # SITE_ENGINEER | SUPERVISOR


def get_current_user(
    authorization: str = Header(default=None),
    x_dev_user_id: str = Header(default=None),
    x_dev_role: str = Header(default=None),
    x_dev_full_name: str = Header(default="Dev User"),
) -> CurrentUser:
    if AUTH_DEV_MODE:
        if x_dev_user_id and x_dev_role:
            if x_dev_role not in ("SITE_ENGINEER", "SUPERVISOR"):
                raise HTTPException(status_code=400, detail="X-Dev-Role must be SITE_ENGINEER or SUPERVISOR")
            return CurrentUser(id=x_dev_user_id, full_name=x_dev_full_name, role=x_dev_role)

        # Allow simple Bearer token shortcuts in dev mode: e.g. "Bearer SITE_ENGINEER"
        if authorization and authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ").strip()
            if token.upper() in ("SITE_ENGINEER", "SUPERVISOR"):
                return CurrentUser(
                    id=f"00000000-0000-0000-0000-{token.lower()[:12].ljust(12, '0')}",
                    full_name=f"Dev {token.title()}",
                    role=token.upper(),
                )

        if not x_dev_user_id or not x_dev_role:
            raise HTTPException(
                status_code=401,
                detail=(
                    "AUTH_DEV_MODE is on (stub shared/auth.py) — send "
                    "X-Dev-User-Id and X-Dev-Role headers to simulate a "
                    "logged-in user until the real auth module lands."
                ),
            )

    # Non-dev path: verify a real Supabase JWT.
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    return CurrentUser(
        id=payload.get("sub", str(uuid.uuid4())),
        full_name=payload.get("user_metadata", {}).get("full_name", "Unknown"),
        role=payload.get("user_metadata", {}).get("role", "SITE_ENGINEER"),
    )


def require_role(*allowed_roles: str):
    """FastAPI dependency factory: require_role("SITE_ENGINEER") -> Depends(...)."""
    from fastapi import Depends

    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Requires role {allowed_roles}, got {user.role}")
        return user

    return _check
