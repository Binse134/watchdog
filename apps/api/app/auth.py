import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import SESSION_COOKIE_NAME, get_current_user
from app.email import send_email
from app.models import User
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    UserOut,
)
from app.security import create_reset_token, create_session_token, hash_password, read_reset_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_KWARGS = dict(httponly=True, samesite="lax", secure=False, path="/")
# Set secure=True once the app is served over HTTPS in production.


@router.post("/signup", response_model=UserOut)
def signup(body: SignupRequest, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_session_token(str(user.id))
    response.set_cookie(SESSION_COOKIE_NAME, token, **COOKIE_KWARGS)
    return user


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = create_session_token(str(user.id))
    response.set_cookie(SESSION_COOKIE_NAME, token, **COOKIE_KWARGS)
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Deletes the account and everything under it (connections, workflows,
    executions, alerts, summaries) via the model cascades on User."""
    db.delete(user)
    db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


@router.patch("/me/password")
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")

    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password updated."}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Always returns the same generic message whether or not the email is
    registered, so this can't be used to discover which emails have an
    account. The actual email send (if any) happens silently in the
    background of this response."""
    user = db.query(User).filter(User.email == body.email).first()
    if user:
        token = create_reset_token(str(user.id))
        reset_link = f"{settings.frontend_url}/reset-password?token={token}"
        html = (
            "<p>Click the link below to reset your Watchdog password. "
            "This link expires in 1 hour.</p>"
            f'<p><a href="{reset_link}">{reset_link}</a></p>'
        )
        send_email(user.email, "Reset your Watchdog password", html)

    return {"message": "If that email has an account, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    user_id = read_reset_token(body.token)
    user = db.get(User, uuid.UUID(user_id)) if user_id else None
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired")

    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password updated. You can now log in."}
