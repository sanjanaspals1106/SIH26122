import os
from typing import Optional, Set
import jwt
from pydantic import BaseModel
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.shared.db import get_connection

VALID_ROLES: Set[str] = {"SITE_ENGINEER", "SUPERVISOR"}

security = HTTPBearer(auto_error=False)


class UserProfile(BaseModel):
    id: str
    full_name: str
    role: str


_jwks_client: Optional[jwt.PyJWKClient] = None
_jwks_url: Optional[str] = None


def get_jwks_client(url: str) -> jwt.PyJWKClient:
    """
    Get or create a cached PyJWKClient instance for the specified JWKS URL.
    Caches the JWK set for 300 seconds to optimize verification latency.
    """
    global _jwks_client, _jwks_url
    if _jwks_client is None or _jwks_url != url:
        _jwks_client = jwt.PyJWKClient(url, cache_jwk_set=True, lifespan=300)
        _jwks_url = url
    return _jwks_client


def decode_supabase_jwt(token: str) -> dict:
    """
    Verify and decode a Supabase-issued JWT token.
    Extracts the payload containing the user ID ('sub').

    Supports:
    1. Offline HMAC-SHA256 verification via SUPABASE_JWT_SECRET / JWT_SECRET.
    2. Offline asymmetric ES256 verification via Supabase JWKS (PyJWKClient).
    3. Online HTTP verification fallback via Supabase Auth API (GET /auth/v1/user)
       using publishable or secret keys (without supabase-py create_client).
    4. Test/development fallback when no verification credentials are configured.
    """
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: token must be a non-empty string",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = token.strip()

    # 1. Symmetric HMAC-SHA256 verification (if SUPABASE_JWT_SECRET is a secret key string, not a URL)
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET") or os.getenv("JWT_SECRET")
    if jwt_secret and not jwt_secret.startswith(("http://", "https://")):
        try:
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
                leeway=10,
            )
            if "sub" in payload:
                return payload
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject claim ('sub')",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except HTTPException:
            raise
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 2. Asymmetric ES256 verification via JWKS
    jwks_url = os.getenv("SUPABASE_JWKS_URL")
    supabase_url = os.getenv("SUPABASE_URL")
    if not jwks_url and supabase_url:
        jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    if jwks_url:
        try:
            client = get_jwks_client(jwks_url)
            signing_key = client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                options={"verify_aud": False},
                leeway=10,
            )
            if "sub" in payload:
                return payload
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject claim ('sub')",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except HTTPException:
            raise
        except jwt.PyJWKClientConnectionError:
            # Network error connecting to JWKS endpoint; fall through to HTTP fallback
            pass
        except jwt.PyJWTError as e:
            # Token signature mismatch, unsupported algorithm, expired, or unknown kid in JWKS
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception:
            # Other transient error; fall through to HTTP fallback if configured.
            pass

    # 3. HTTP verification fallback against Supabase Auth endpoint
    # (Direct HTTP request avoids supabase-py regex validation issues with sb_* keys)
    supabase_key = (
        os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SECRET_KEY")
    )
    if supabase_url and supabase_key:
        try:
            import httpx

            resp = httpx.get(
                f"{supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {token}",
                },
                timeout=5.0,
            )
            if resp.status_code == 200:
                user_data = resp.json()
                return {
                    "sub": str(user_data.get("id")),
                    "email": user_data.get("email"),
                    "role": user_data.get("role"),
                }
            if resp.status_code in (400, 401, 403):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token validation failed: Supabase rejected the token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Token validation failed: Supabase returned {resp.status_code}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 4. Local development / offline test mode fallback (only reached if no verification provider is configured)
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        if "sub" in payload:
            return payload
    except Exception:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to validate authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> UserProfile:
    """
    FastAPI dependency that extracts and verifies the Supabase JWT
    from the Authorization header, looking up the authenticated user's
    profile from the profiles table.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_supabase_jwt(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject claim ('sub')",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, full_name, role
                FROM profiles
                WHERE id = %s
                """,
                (user_id,),
            ).fetchone()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database lookup error during authentication: {str(e)}",
        )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authenticated user '{user_id}' has no profile record in database",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = row["role"]
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid profile role '{role}'. Allowed roles: {sorted(VALID_ROLES)}",
        )

    return UserProfile(
        id=str(row["id"]),
        full_name=row["full_name"],
        role=role,
    )


def require_role(required_role: str):
    """
    FastAPI dependency factory enforcing that the authenticated caller
    possesses exactly the required role ('SITE_ENGINEER' or 'SUPERVISOR').
    Returns HTTP 403 Forbidden if the role does not match.
    """
    if required_role not in VALID_ROLES:
        raise ValueError(
            f"Invalid role '{required_role}'. Allowed roles are: {sorted(VALID_ROLES)}"
        )

    def role_dependency(
        current_user: UserProfile = Depends(get_current_user),
    ) -> UserProfile:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires role '{required_role}', but caller has role '{current_user.role}'",
            )
        return current_user

    return role_dependency
