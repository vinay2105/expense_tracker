import unittest

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies import get_current_user, get_optional_user
from app.security import create_access_token


class AuthenticationTests(unittest.TestCase):
    def test_valid_bearer_token_returns_payload(self):
        token = create_access_token(
            {"sub": "1", "email": "test@example.com"}
        )
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        payload = get_current_user(credentials, None)

        self.assertEqual(payload["sub"], "1")
        self.assertEqual(payload["email"], "test@example.com")

    def test_missing_credentials_returns_401(self):
        with self.assertRaises(HTTPException) as context:
            get_current_user(None, None)

        self.assertEqual(context.exception.status_code, 401)

    def test_invalid_token_returns_401(self):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="not-a-jwt",
        )

        with self.assertRaises(HTTPException) as context:
            get_current_user(credentials, None)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(
            context.exception.detail,
            "Invalid or expired token",
        )

    def test_valid_cookie_token_returns_payload(self):
        token = create_access_token(
            {"sub": "2", "email": "cookie@example.com"}
        )

        payload = get_current_user(None, token)

        self.assertEqual(payload["sub"], "2")
        self.assertEqual(payload["email"], "cookie@example.com")

    def test_optional_user_returns_none_without_cookie(self):
        self.assertIsNone(get_optional_user(None))

    def test_optional_user_returns_payload_for_valid_cookie(self):
        token = create_access_token(
            {"sub": "3", "email": "returning@example.com"}
        )

        payload = get_optional_user(token)

        self.assertEqual(payload["email"], "returning@example.com")


if __name__ == "__main__":
    unittest.main()
