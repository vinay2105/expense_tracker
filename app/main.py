from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.database import engine, Base
from app.models.user import User

from app.dependencies import (
    get_current_user,
    get_dashboard_user,
    get_optional_user,
)

from sqlalchemy.orm import Session
from fastapi import Depends
from app.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token

from app.dependencies import get_db
from app.schemas.user import UserCreate, UserResponse
from app.crud.user import create_user
from app.schemas.auth import LoginRequest
from app.crud.user import authenticate_user
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
def landing_page(
    request: Request,
    current_user=Depends(get_optional_user),
):
    if current_user:
        return RedirectResponse(
            url="/dashboard",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="landing.html"
    )

@app.get("/login")
def login_page(
    request: Request,
    current_user=Depends(get_optional_user),
):
    if current_user:
        return RedirectResponse(
            url="/dashboard",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

@app.get("/signup")
def signup_page(
    request: Request,
    current_user=Depends(get_optional_user),
):
    if current_user:
        return RedirectResponse(
            url="/dashboard",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="signup.html"
    )

@app.get("/dashboard")
def dashboard_page(
    request: Request,
    current_user=Depends(get_dashboard_user),
):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"current_user": current_user},
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


@app.post("/login")
def login(
    credentials: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    user = authenticate_user(
        db,
        credentials.email,
        credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    token = create_access_token(
        {
            "sub" : str(user.id),
            "email": user.email
        }
    )

    response.set_cookie(
        key="access_token",
        value=token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@app.post("/logout")
def logout():
    response = RedirectResponse(
        url="/login",
        status_code=303,
    )
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
    )
    return response



@app.get("/me")
def me(current_user = Depends(get_current_user)):
    return current_user
