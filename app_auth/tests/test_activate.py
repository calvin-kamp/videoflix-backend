"""Tests for ``GET /api/activate/<uidb64>/<token>/``."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from app_auth.tokens import account_activation_token

from .utils import create_user, encode_uid


class ActivateTests(APITestCase):
    def setUp(self):
        self.user = create_user(is_active=False)
        self.token = account_activation_token.make_token(self.user)

    def url(self, uidb64, token):
        return reverse("activate", args=[uidb64, token])

    def test_activates_account(self):
        response = self.client.get(self.url(encode_uid(self.user), self.token))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"message": "Account successfully activated."})
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_rejects_invalid_token(self):
        response = self.client.get(self.url(encode_uid(self.user), "invalid-token"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_rejects_invalid_uid(self):
        response = self.client.get(self.url("invalid", self.token))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_can_only_be_used_once(self):
        url = self.url(encode_uid(self.user), self.token)
        self.client.get(url)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
