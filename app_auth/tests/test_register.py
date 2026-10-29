"""Tests for ``POST /api/register/``."""

from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from app_auth.tokens import account_activation_token

from .utils import PASSWORD, User, create_user, encode_uid, enqueue_synchronously


class RegisterTests(APITestCase):
    url = reverse("register")

    def setUp(self):
        enqueue_synchronously(self)

    def payload(self, **overrides):
        data = {
            "email": "new@example.com",
            "password": PASSWORD,
            "confirmed_password": PASSWORD,
        }
        data.update(overrides)
        return data

    def test_creates_inactive_user(self):
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="new@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(user.username, "new@example.com")
        self.assertTrue(user.check_password(PASSWORD))

    def test_response_contains_user_and_token(self):
        response = self.client.post(self.url, self.payload(), format="json")

        user = User.objects.get(email="new@example.com")
        self.assertEqual(
            response.data["user"], {"id": user.id, "email": "new@example.com"}
        )
        self.assertTrue(
            account_activation_token.check_token(user, response.data["token"])
        )

    def test_sends_activation_email(self):
        response = self.client.post(self.url, self.payload(), format="json")

        user = User.objects.get(email="new@example.com")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["new@example.com"])
        html_body = message.alternatives[0].content
        self.assertIn(f"uid={encode_uid(user)}", html_body)
        self.assertIn(f"token={response.data['token']}", html_body)

    def test_activation_email_has_text_part_and_inline_logo(self):
        response = self.client.post(self.url, self.payload(), format="json")

        message = mail.outbox[0]
        self.assertIn(f"token={response.data['token']}", message.body)
        self.assertNotIn("&amp;", message.body)
        mime = message.message()
        logo = next(part for part in mime.walk() if part.get("Content-ID"))
        self.assertEqual(logo["Content-ID"], "<videoflix-logo>")
        self.assertEqual(logo.get_content_type(), "image/png")

    def test_rejects_mismatching_passwords(self):
        response = self.client.post(
            self.url, self.payload(confirmed_password="Other!Passw0rd"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="new@example.com").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_rejects_existing_email(self):
        create_user(email="new@example.com")

        response = self.client.post(
            self.url, self.payload(email="NEW@example.com"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)

    def test_rejects_invalid_email(self):
        response = self.client.post(
            self.url, self.payload(email="not-an-email"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_weak_password(self):
        response = self.client.post(
            self.url,
            self.payload(password="123", confirmed_password="123"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
