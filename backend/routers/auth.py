from fastapi import APIRouter, Depends

from backend.shared.auth import UserProfile, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=UserProfile)
def get_me(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
    """
    Return the profile of the currently authenticated user.
    Identity and role are derived exclusively from the verified token
    and profiles table lookup.
    """
    return current_user
