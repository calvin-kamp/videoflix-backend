"""Tests for ``POST /api/token/refresh/``."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .utils import create_user


class TokenRefreshTests(APITestCase):
    url = reverse("token_refresh")

    def setUp(self):
        self.user = create_user()
        self.client.cookies["refresh_token"] = str(RefreshToken.for_user(self.user))

    def test_returns_new_access_token(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "Token refreshed")
        self.assertEqual(
            AccessToken(response.data["access"])["user_id"], str(self.user.id)
        )

    def test_sets_access_cookie(self):
        response = self.client.post(self.url)

        cookie = response.cookies["access_token"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie.value, response.data["access"])

    def test_rejects_missing_refresh_cookie(self):
        del self.client.cookies["refresh_token"]

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_invalid_refresh_cookie(self):
        self.client.cookies["refresh_token"] = "invalid"

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
