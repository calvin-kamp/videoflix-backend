"""Tests for ``POST /api/login/``."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .utils import PASSWORD, create_user


class LoginTests(APITestCase):
    url = reverse("login")

    def setUp(self):
        self.user = create_user()

    def login(self, email="user@example.com", password=PASSWORD):
        return self.client.post(
            self.url, {"email": email, "password": password}, format="json"
        )

    def test_returns_user(self):
        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "detail": "Login successful",
                "user": {"id": self.user.id, "username": "user@example.com"},
            },
        )

    def test_sets_http_only_token_cookies(self):
        response = self.login()

        access_cookie = response.cookies["access_token"]
        refresh_cookie = response.cookies["refresh_token"]
        self.assertTrue(access_cookie["httponly"])
        self.assertTrue(refresh_cookie["httponly"])
        self.assertEqual(AccessToken(access_cookie.value)["user_id"], str(self.user.id))
        self.assertEqual(RefreshToken(refresh_cookie.value)["user_id"], str(self.user.id))

    def test_email_is_case_insensitive(self):
        response = self.login(email="USER@example.com")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_rejects_wrong_password(self):
        response = self.login(password="Wrong!Passw0rd")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("access_token", response.cookies)

    def test_rejects_unknown_email(self):
        response = self.login(email="unknown@example.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_inactive_user(self):
        create_user(email="inactive@example.com", is_active=False)

        response = self.login(email="inactive@example.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ignores_invalid_access_cookie(self):
        self.client.cookies["access_token"] = "expired-or-invalid"

        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
