"""Public registration/login and the current-user profile endpoint."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.core.enums import UserRole
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.dependencies import get_db
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserResponse
from app.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    """Create a student account. Role escalation via the request is impossible."""
    if db.scalar(select(User.id).where(User.email == payload.email)):
        raise AppError("An account with that email already exists", 409, code="duplicate_email")

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.STUDENT.value,
        department_id=None,
        is_active=True,
    )
    db.add(user)
    try:
        db.flush()
        record_audit(
            db,
            actor=user,
            action="auth.registered",
            entity_type="user",
            entity_id=user.id,
            details={"email": user.email},
            is_override=False,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError("An account with that email already exists", 409, code="duplicate_email") from exc
    db.refresh(user)
    return user


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Exchange valid credentials for a short-lived bearer token."""
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
        # One generic message for all failures: do not disclose which field was wrong.
        reason = "user_not_found"
        if user is not None and not user.is_active:
            reason = "inactive_account"
        elif user is not None:
            reason = "invalid_credentials"
        record_audit(
            db,
            actor=user,
            actor_role=user.role if user is not None else None,
            action="auth.login_failed",
            entity_type="user",
            entity_id=user.id if user is not None else payload.email,
            details={"email": payload.email, "reason": reason},
            is_override=False,
        )
        db.commit()
        raise AppError("Invalid email or password", 401, code="invalid_credentials")

    record_audit(
        db,
        actor=user,
        action="auth.login_succeeded",
        entity_type="user",
        entity_id=user.id,
        details={"email": user.email},
        is_override=False,
    )
    db.commit()

    token, expires_in = create_access_token(user.id, user.role)
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def read_current_user(user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's profile (never the password hash)."""
    return user
