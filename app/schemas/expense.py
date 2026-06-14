from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpenseCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=255)
    payment_method: str = Field(default="Other", min_length=1, max_length=50)
    expense_date: date = Field(default_factory=date.today)

    @field_validator("category", "description", "payment_method")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class ExpenseResponse(BaseModel):
    id: int
    amount: Decimal
    category: str
    description: str
    payment_method: str
    expense_date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategorySummary(BaseModel):
    name: str
    total: Decimal
    count: int
    percentage: float


class ExpenseSummaryResponse(BaseModel):
    month_total: Decimal
    total_expenses: Decimal
    transaction_count: int
    month_count: int
    daily_average: Decimal
    top_category: CategorySummary | None
    categories: list[CategorySummary]
    month_name: str
