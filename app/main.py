from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.crud.expense import (
    create_expense,
    delete_expense,
    get_dashboard_statistics,
    get_recent_expenses,
)
from app.crud.user import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_username,
)
from app.database import Base, engine
from app.dependencies import (
    get_current_user,
    get_dashboard_user,
    get_db,
    get_optional_user,
)
from app.models.expense import Expense
from app.models.user import User
from app.api.expenses import router as expense_api_router
from app.mcp_server import mcp_http_app
from app.schemas.auth import LoginRequest
from app.schemas.expense import ExpenseCreate, ExpenseResponse
from app.schemas.user import UserCreate, UserResponse
from app.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token


app = FastAPI(lifespan=mcp_http_app.lifespan)

Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")
app.include_router(expense_api_router)
app.mount("/mcp", mcp_http_app)


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
    db: Session = Depends(get_db),
):
    user_id = int(current_user["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie("access_token")
        return response

    statistics = get_dashboard_statistics(db, user_id)
    recent_expenses = get_recent_expenses(db, user_id)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "current_user": user,
            "statistics": statistics,
            "recent_expenses": recent_expenses,
        },
    )


@app.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_expense(
    expense: ExpenseCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_expense(db, int(current_user["sub"]), expense)


@app.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_expense(
    expense_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not delete_expense(db, int(current_user["sub"]), expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")

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
