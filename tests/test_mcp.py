import asyncio
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.mcp_server import mcp
from app.models.expense import Expense
from app.models.user import User
from app.schemas.expense import ExpenseCreate
from app.security import create_access_token


class McpServerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
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
                        amount=Decimal("20.00"),
                        category="Food & Dining",
                        description="First user's lunch",
                        payment_method="UPI",
                        expense_date=date.today(),
                    ),
                    Expense(
                        user_id=second.id,
                        amount=Decimal("900.00"),
                        category="Travel",
                        description="Second user's flight",
                        payment_method="Credit card",
                        expense_date=date.today(),
                    ),
                ]
            )
            db.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_tool_discovery_only_exposes_expense_tools_without_user_id(self):
        tools = asyncio.run(mcp.list_tools())
        names = {tool.name for tool in tools}

        self.assertEqual(
            names,
            {
                "get_my_expense_summary",
                "list_my_recent_expenses",
                "search_my_expenses",
                "get_my_category_breakdown",
                "add_my_expense",
                "delete_my_expense",
            },
        )

        for tool in tools:
            properties = tool.parameters.get("properties", {})
            self.assertNotIn("user_id", properties)
            self.assertNotIn("subject", properties)

    def test_mcp_list_tool_is_scoped_to_authenticated_subject(self):
        tool = asyncio.run(mcp.get_tool("list_my_recent_expenses"))

        with patch("app.mcp_server.SessionLocal", self.session_factory):
            first_result = tool.fn(limit=10, subject=str(self.first_user_id))
            second_result = tool.fn(limit=10, subject=str(self.second_user_id))

        self.assertEqual(
            [item["description"] for item in first_result],
            ["First user's lunch"],
        )
        self.assertEqual(
            [item["description"] for item in second_result],
            ["Second user's flight"],
        )

    def test_mcp_delete_tool_cannot_delete_another_users_expense(self):
        with self.session_factory() as db:
            second_expense_id = (
                db.query(Expense)
                .filter(Expense.user_id == self.second_user_id)
                .one()
                .id
            )

        tool = asyncio.run(mcp.get_tool("delete_my_expense"))

        with patch("app.mcp_server.SessionLocal", self.session_factory):
            with self.assertRaises(Exception):
                tool.fn(
                    expense_id=second_expense_id,
                    subject=str(self.first_user_id),
                )

        with self.session_factory() as db:
            self.assertIsNotNone(db.get(Expense, second_expense_id))

    def test_mcp_jwt_verifier_accepts_valid_token_and_rejects_invalid_token(self):
        token = create_access_token(
            {"sub": str(self.first_user_id), "email": "first@example.com"}
        )

        valid = asyncio.run(mcp.auth.verify_token(token))
        invalid = asyncio.run(mcp.auth.verify_token("not-a-token"))

        self.assertEqual(valid.claims["sub"], str(self.first_user_id))
        self.assertIsNone(invalid)


if __name__ == "__main__":
    unittest.main()
