import unittest
from datetime import date
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.expenses import router
from app.database import Base
from app.dependencies import get_current_user, get_db
from app.models.expense import Expense
from app.models.user import User


class ExpenseApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)

        with self.session_factory() as db:
            first = User(
                username="first",
                email="first@example.com",
                password_hash="not-used",
            )
            second = User(
                username="second",
                email="second@example.com",
                password_hash="not-used",
            )
            db.add_all([first, second])
            db.commit()
            self.first_user_id = first.id
            self.second_user_id = second.id
            db.add_all(
                [
                    Expense(
                        user_id=first.id,
                        amount=Decimal("25.00"),
                        category="Food & Dining",
                        description="First lunch",
                        payment_method="UPI",
                        expense_date=date.today(),
                    ),
                    Expense(
                        user_id=second.id,
                        amount=Decimal("800.00"),
                        category="Travel",
                        description="Second flight",
                        payment_method="Credit card",
                        expense_date=date.today(),
                    ),
                ]
            )
            db.commit()

        app = FastAPI()
        app.include_router(router)

        def override_db():
            with self.session_factory() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: {
            "sub": str(self.first_user_id),
            "email": "first@example.com",
        }
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def test_recent_endpoint_only_returns_authenticated_users_expenses(self):
        response = self.client.get("/api/expenses/recent")

        self.assertEqual(response.status_code, 200)
        descriptions = [item["description"] for item in response.json()]
        self.assertEqual(descriptions, ["First lunch"])

    def test_delete_endpoint_hides_another_users_expense(self):
        with self.session_factory() as db:
            second_expense_id = (
                db.query(Expense)
                .filter(Expense.user_id == self.second_user_id)
                .one()
                .id
            )

        response = self.client.delete(f"/api/expenses/{second_expense_id}")

        self.assertEqual(response.status_code, 404)
        with self.session_factory() as db:
            self.assertIsNotNone(db.get(Expense, second_expense_id))


if __name__ == "__main__":
    unittest.main()
