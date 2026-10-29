"""Tests for ``POST /api/password_reset/``."""

from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .utils import create_user, encode_uid, enqueue_synchronously


class PasswordResetTests(APITestCase):
    url = reverse("password_reset")

    def setUp(self):
        enqueue_synchronously(self)
        self.user = create_user()

    def test_sends_reset_email(self):
        response = self.client.post(
            self.url, {"email": "user@example.com"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"detail": "An email has been sent to reset your password."}
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["user@example.com"])
        self.assertIn(
            f"uid={encode_uid(self.user)}", mail.outbox[0].alternatives[0].content
        )

    def test_unknown_email_gets_same_response_without_email(self):
        response = self.client.post(
            self.url, {"email": "unknown@example.com"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_rejects_invalid_email(self):
        response = self.client.post(self.url, {"email": "invalid"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
