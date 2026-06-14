from datetime import date
from decimal import Decimal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import JWTVerifier
from fastmcp.server.dependencies import TokenClaim
from pydantic import Field
from typing_extensions import Annotated

from app.crud.expense import (
    create_expense,
    delete_expense,
    get_dashboard_statistics,
    get_recent_expenses,
    search_expenses,
)
from app.database import SessionLocal
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseResponse,
    ExpenseSummaryResponse,
)
from app.security import ALGORITHM, SECRET_KEY


mcp = FastMCP(
    name="Spendly Expense MCP",
    instructions=(
        "Tools for the authenticated user's expenses. The user identity comes "
        "from the verified bearer token and must never be requested from the user."
    ),
    auth=JWTVerifier(public_key=SECRET_KEY, algorithm=ALGORITHM),
)


def trusted_user_id(subject: str) -> int:
    try:
        return int(subject)
    except (TypeError, ValueError) as exc:
        raise ToolError("The authenticated token has an invalid subject.") from exc


def expense_data(expense) -> dict:
    return ExpenseResponse.model_validate(expense).model_dump(mode="json")


@mcp.tool(
    name="get_my_expense_summary",
    description=(
        "Get the authenticated user's spending totals, daily average, top "
        "category, and category breakdown for the current month."
    ),
)
def get_my_expense_summary(
    subject: str = TokenClaim("sub"),
) -> dict:
    user_id = trusted_user_id(subject)
    with SessionLocal() as db:
        summary = get_dashboard_statistics(db, user_id)
        return ExpenseSummaryResponse.model_validate(summary).model_dump(mode="json")


@mcp.tool(
    name="list_my_recent_expenses",
    description="List the authenticated user's most recent expenses.",
)
def list_my_recent_expenses(
    limit: Annotated[int, Field(ge=1, le=100)] = 10,
    subject: str = TokenClaim("sub"),
) -> list[dict]:
    user_id = trusted_user_id(subject)
    with SessionLocal() as db:
        return [
            expense_data(expense)
            for expense in get_recent_expenses(db, user_id, limit)
        ]


@mcp.tool(
    name="search_my_expenses",
    description=(
        "Search the authenticated user's expenses by category, date range, or "
        "description text. All filters are optional."
    ),
)
def search_my_expenses(
    category: Annotated[str | None, Field(max_length=50)] = None,
    start_date: date | None = None,
    end_date: date | None = None,
    description: Annotated[str | None, Field(max_length=255)] = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
    subject: str = TokenClaim("sub"),
) -> list[dict]:
    if start_date and end_date and start_date > end_date:
        raise ToolError("start_date must be on or before end_date")

    user_id = trusted_user_id(subject)
    with SessionLocal() as db:
        expenses = search_expenses(
            db,
            user_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
            description=description,
            limit=limit,
        )
        return [expense_data(expense) for expense in expenses]


@mcp.tool(
    name="get_my_category_breakdown",
    description=(
        "Get the authenticated user's category totals and percentages for the "
        "current month."
    ),
)
def get_my_category_breakdown(
    subject: str = TokenClaim("sub"),
) -> list[dict]:
    user_id = trusted_user_id(subject)
    with SessionLocal() as db:
        summary = get_dashboard_statistics(db, user_id)
        return [
            {
                **category,
                "total": str(category["total"]),
            }
            for category in summary["categories"]
        ]


@mcp.tool(
    name="add_my_expense",
    description=(
        "Add an expense for the authenticated user. Use only when the user "
        "clearly asks to record an expense."
    ),
)
def add_my_expense(
    amount: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)],
    category: Annotated[str, Field(min_length=1, max_length=50)],
    description: Annotated[str, Field(min_length=1, max_length=255)],
    payment_method: Annotated[str, Field(min_length=1, max_length=50)] = "Other",
    expense_date: date = Field(default_factory=date.today),
    subject: str = TokenClaim("sub"),
) -> dict:
    user_id = trusted_user_id(subject)
    expense = ExpenseCreate(
        amount=amount,
        category=category,
        description=description,
        payment_method=payment_method,
        expense_date=expense_date,
    )
    with SessionLocal() as db:
        return expense_data(create_expense(db, user_id, expense))


@mcp.tool(
    name="delete_my_expense",
    description=(
        "Delete one expense owned by the authenticated user. The agent must "
        "obtain explicit user confirmation before calling this destructive tool."
    ),
)
def delete_my_expense(
    expense_id: Annotated[int, Field(gt=0)],
    subject: str = TokenClaim("sub"),
) -> dict:
    user_id = trusted_user_id(subject)
    with SessionLocal() as db:
        if not delete_expense(db, user_id, expense_id):
            raise ToolError("Expense not found.")
    return {"deleted": True, "expense_id": expense_id}


mcp_http_app = mcp.http_app(path="/", stateless_http=True)
