"""Tests for ``POST /api/logout/``."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from .utils import create_user


class LogoutTests(APITestCase):
    url = reverse("logout")

    def setUp(self):
        self.user = create_user()
        self.refresh = RefreshToken.for_user(self.user)
        self.client.cookies["access_token"] = str(self.refresh.access_token)
        self.client.cookies["refresh_token"] = str(self.refresh)

    def test_logs_out(self):
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["detail"],
            "Logout successful! All tokens will be deleted. "
            "Refresh token is now invalid.",
        )

    def test_blacklists_refresh_token(self):
        self.client.post(self.url)

        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=self.refresh["jti"]).exists()
        )

    def test_deletes_token_cookies(self):
        response = self.client.post(self.url)

        for name in ("access_token", "refresh_token"):
            self.assertEqual(response.cookies[name].value, "")
            self.assertEqual(response.cookies[name]["max-age"], 0)

    def test_refresh_token_is_unusable_afterwards(self):
        raw_refresh = str(self.refresh)
        self.client.post(self.url)

        self.client.cookies["refresh_token"] = raw_refresh
        response = self.client.post(reverse("token_refresh"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rejects_missing_refresh_cookie(self):
        del self.client.cookies["refresh_token"]

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_invalid_refresh_cookie(self):
        self.client.cookies["refresh_token"] = "invalid"

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
