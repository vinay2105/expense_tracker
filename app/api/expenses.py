from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.expense import (
    create_expense,
    delete_expense,
    get_dashboard_statistics,
    get_recent_expenses,
    search_expenses,
)
from app.dependencies import get_current_user, get_db
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseResponse,
    ExpenseSummaryResponse,
)


router = APIRouter(
    prefix="/api/expenses",
    tags=["expense-api"],
    dependencies=[Depends(get_current_user)],
)


def current_user_id(current_user: dict = Depends(get_current_user)) -> int:
    return int(current_user["sub"])


@router.get(
    "/summary",
    response_model=ExpenseSummaryResponse,
    operation_id="get_my_expense_summary",
    summary="Get my expense summary",
)
def expense_summary(
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    return get_dashboard_statistics(db, user_id)


@router.get(
    "/recent",
    response_model=list[ExpenseResponse],
    operation_id="list_my_recent_expenses",
    summary="List my recent expenses",
)
def recent_expenses(
    limit: int = Query(default=10, ge=1, le=100),
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    return get_recent_expenses(db, user_id, limit)


@router.get(
    "/search",
    response_model=list[ExpenseResponse],
    operation_id="search_my_expenses",
    summary="Search my expenses",
)
def expense_search(
    category: str | None = Query(default=None, max_length=50),
    start_date: date | None = None,
    end_date: date | None = None,
    description: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date must be on or before end_date",
        )

    return search_expenses(
        db,
        user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        description=description,
        limit=limit,
    )


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="add_my_expense",
    summary="Add an expense for the authenticated user",
)
def add_expense_api(
    expense: ExpenseCreate,
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    return create_expense(db, user_id, expense)


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_my_expense",
    summary="Delete one of my expenses",
)
def delete_expense_api(
    expense_id: int,
    user_id: int = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    if not delete_expense(db, user_id, expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")
