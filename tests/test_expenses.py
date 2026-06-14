import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.crud.expense import (
    create_expense,
    delete_expense,
    get_dashboard_statistics,
    get_recent_expenses,
    search_expenses,
)
from app.database import Base
from app.models.expense import Expense
from app.models.user import User
from app.schemas.expense import ExpenseCreate


class ExpenseTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        session = sessionmaker(bind=self.engine)
        self.db = session()

        self.first_user = User(
            username="first",
            email="first@example.com",
            password_hash="not-used",
        )
        self.second_user = User(
            username="second",
            email="second@example.com",
            password_hash="not-used",
        )
        self.db.add_all([self.first_user, self.second_user])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def add_expense(
        self,
        user_id: int,
        amount: str,
        category: str,
        expense_date: date,
        description: str = "Test expense",
    ) -> Expense:
        return create_expense(
            self.db,
            user_id,
            ExpenseCreate(
                amount=Decimal(amount),
                category=category,
                description=description,
                payment_method="UPI",
                expense_date=expense_date,
            ),
        )

    def test_statistics_are_scoped_to_user_and_month(self):
        self.add_expense(
            self.first_user.id,
            "120.50",
            "Food & Dining",
            date(2026, 6, 2),
        )
        self.add_expense(
            self.first_user.id,
            "79.50",
            "Food & Dining",
            date(2026, 6, 10),
        )
        self.add_expense(
            self.first_user.id,
            "300.00",
            "Travel",
            date(2026, 5, 20),
        )
        self.add_expense(
            self.second_user.id,
            "9999.00",
            "Shopping",
            date(2026, 6, 4),
        )

        stats = get_dashboard_statistics(
            self.db,
            self.first_user.id,
            today=date(2026, 6, 14),
        )

        self.assertEqual(stats["month_total"], Decimal("200.00"))
        self.assertEqual(stats["total_expenses"], Decimal("500.00"))
        self.assertEqual(stats["transaction_count"], 3)
        self.assertEqual(stats["month_count"], 2)
        self.assertEqual(stats["top_category"]["name"], "Food & Dining")
        self.assertAlmostEqual(
            stats["daily_average"],
            Decimal("14.28571428571428571428571429"),
        )

    def test_recent_expenses_only_returns_owners_rows(self):
        owned = self.add_expense(
            self.first_user.id,
            "25.00",
            "Transport",
            date(2026, 6, 12),
        )
        self.add_expense(
            self.second_user.id,
            "50.00",
            "Health",
            date(2026, 6, 13),
        )

        recent = get_recent_expenses(self.db, self.first_user.id)

        self.assertEqual([expense.id for expense in recent], [owned.id])

    def test_user_cannot_delete_another_users_expense(self):
        expense = self.add_expense(
            self.second_user.id,
            "75.00",
            "Entertainment",
            date(2026, 6, 14),
        )

        deleted = delete_expense(self.db, self.first_user.id, expense.id)

        self.assertFalse(deleted)
        self.assertIsNotNone(self.db.get(Expense, expense.id))

    def test_search_filters_only_the_owners_expenses(self):
        matching = self.add_expense(
            self.first_user.id,
            "125.00",
            "Food & Dining",
            date(2026, 6, 14),
            description="Sunday groceries",
        )
        self.add_expense(
            self.first_user.id,
            "50.00",
            "Transport",
            date(2026, 6, 14),
            description="Metro card",
        )
        self.add_expense(
            self.second_user.id,
            "999.00",
            "Food & Dining",
            date(2026, 6, 14),
            description="Sunday groceries",
        )

        results = search_expenses(
            self.db,
            self.first_user.id,
            category="Food & Dining",
            description="grocer",
        )

        self.assertEqual([expense.id for expense in results], [matching.id])


if __name__ == "__main__":
    unittest.main()
