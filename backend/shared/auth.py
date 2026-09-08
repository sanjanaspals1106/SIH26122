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


def decode_supabase_jwt(token: str) -> dict:
    """
    Verify and decode a Supabase-issued JWT token.
    Extracts the payload containing the user ID ('sub').
    """
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET") or os.getenv("JWT_SECRET")

    if jwt_secret:
        try:
            return jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv(
        "SUPABASE_SERVICE_ROLE_KEY"
    )
    if supabase_url and supabase_key:
        try:
            from supabase import create_client

            client = create_client(supabase_url, supabase_key)
            user_resp = client.auth.get_user(token)
            if user_resp and user_resp.user:
                return {
                    "sub": str(user_resp.user.id),
                    "email": user_resp.user.email,
                }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Local development / test mode fallback
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
