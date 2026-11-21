"""Authentication and authorization dependencies for protected routes."""

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.dependencies import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    """Decode the bearer token and load the active user from the database."""
    if credentials is None:
        raise AppError("Authentication required", 401, code="not_authenticated")

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError("Invalid access token", 401, code="invalid_token") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError("Invalid or inactive account", 401, code="invalid_token")
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    """Build a dependency that only allows the given roles."""
    allowed = {role.value for role in roles}

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise AppError("You do not have permission for this action", 403, code="forbidden")
        return user

    return checker


require_student = require_roles(UserRole.STUDENT)
require_staff = require_roles(UserRole.STAFF)
require_hod = require_roles(UserRole.HOD)
require_admin = require_roles(UserRole.ADMIN)
require_staff_or_above = require_roles(UserRole.STAFF, UserRole.HOD, UserRole.ADMIN)
require_hod_or_admin = require_roles(UserRole.HOD, UserRole.ADMIN)
