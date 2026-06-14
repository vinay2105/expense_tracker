from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.schemas.expense import ExpenseCreate


def create_expense(db: Session, user_id: int, expense: ExpenseCreate) -> Expense:
    new_expense = Expense(user_id=user_id, **expense.model_dump())
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    return new_expense


def get_recent_expenses(
    db: Session,
    user_id: int,
    limit: int = 10,
) -> list[Expense]:
    return (
        db.query(Expense)
        .filter(Expense.user_id == user_id)
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .limit(limit)
        .all()
    )


def search_expenses(
    db: Session,
    user_id: int,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    description: str | None = None,
    limit: int = 20,
) -> list[Expense]:
    query = db.query(Expense).filter(Expense.user_id == user_id)

    if category:
        query = query.filter(Expense.category == category.strip())
    if start_date:
        query = query.filter(Expense.expense_date >= start_date)
    if end_date:
        query = query.filter(Expense.expense_date <= end_date)
    if description:
        query = query.filter(Expense.description.ilike(f"%{description.strip()}%"))

    return (
        query.order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )


def delete_expense(db: Session, user_id: int, expense_id: int) -> bool:
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.user_id == user_id)
        .first()
    )
    if expense is None:
        return False

    db.delete(expense)
    db.commit()
    return True


def get_dashboard_statistics(
    db: Session,
    user_id: int,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    month_start = today.replace(day=1)
    month_end = today.replace(day=monthrange(today.year, today.month)[1])

    total_expenses, transaction_count = (
        db.query(
            func.coalesce(func.sum(Expense.amount), 0),
            func.count(Expense.id),
        )
        .filter(Expense.user_id == user_id)
        .one()
    )

    month_total, month_count = (
        db.query(
            func.coalesce(func.sum(Expense.amount), 0),
            func.count(Expense.id),
        )
        .filter(
            Expense.user_id == user_id,
            Expense.expense_date >= month_start,
            Expense.expense_date <= month_end,
        )
        .one()
    )

    category_rows = (
        db.query(
            Expense.category,
            func.sum(Expense.amount).label("total"),
            func.count(Expense.id).label("count"),
        )
        .filter(
            Expense.user_id == user_id,
            Expense.expense_date >= month_start,
            Expense.expense_date <= month_end,
        )
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    month_total = Decimal(month_total)
    total_expenses = Decimal(total_expenses)
    days_elapsed = max(today.day, 1)
    daily_average = month_total / days_elapsed

    categories = [
        {
            "name": row.category,
            "total": Decimal(row.total),
            "count": row.count,
            "percentage": (
                float((Decimal(row.total) / month_total) * 100)
                if month_total
                else 0
            ),
        }
        for row in category_rows
    ]

    return {
        "month_total": month_total,
        "total_expenses": total_expenses,
        "transaction_count": transaction_count,
        "month_count": month_count,
        "daily_average": daily_average,
        "top_category": categories[0] if categories else None,
        "categories": categories,
        "month_name": today.strftime("%B"),
    }
