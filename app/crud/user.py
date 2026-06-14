from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate


def create_user(db: Session, user: UserCreate):
    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=user.password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

def get_user_by_email(db: Session, email: str):
    return (
        db.query(User)
        .filter(User.email == email)
        .first()
    )


def get_user_by_username(db: Session, username: str):
    return (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)

    if not user:
        return None

    if user.password_hash != password:
        return None

    return user