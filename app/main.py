from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from app.database import engine, Base
from app.models.user import User

from sqlalchemy.orm import Session
from fastapi import Depends

from app.dependencies import get_db
from app.schemas.user import UserCreate, UserResponse
from app.crud.user import create_user
from fastapi import HTTPException
from app.crud.user import (
    create_user,
    get_user_by_email,
    get_user_by_username
)


app = FastAPI()

Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")


@app.get("/")
def landing_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="landing.html"
    )

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

@app.get("/signup")
def signup_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="signup.html"
    )

@app.get("/dashboard")
def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html"
    )

@app.post("/signup", response_model=UserResponse)
def signup(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    
    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    if get_user_by_username(db, user.username):
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )

    return create_user(db, user)