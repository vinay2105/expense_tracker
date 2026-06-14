from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = Column(Numeric(12, 2), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    payment_method = Column(String(50), nullable=False, default="Other")
    expense_date = Column(Date, nullable=False, default=date.today, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    user = relationship("User", back_populates="expenses")
