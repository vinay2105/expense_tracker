from app.database import SessionLocal
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.security import verify_token


bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Enter the access token returned by POST /login.",
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    access_token: Annotated[str | None, Cookie()] = None,
):
    token = credentials.credentials if credentials else access_token

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials and credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def get_dashboard_user(
    access_token: Annotated[str | None, Cookie()] = None,
):
    payload = get_optional_user(access_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )

    return payload


def get_optional_user(
    access_token: Annotated[str | None, Cookie()] = None,
):
    return verify_token(access_token) if access_token else None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
