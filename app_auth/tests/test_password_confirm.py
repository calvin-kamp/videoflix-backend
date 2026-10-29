"""Tests for ``POST /api/password_confirm/<uidb64>/<token>/``."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .utils import PASSWORD, create_user, encode_uid, make_password_reset_token

NEW_PASSWORD = "N3w!SecurePassw0rd"


class PasswordConfirmTests(APITestCase):
    def setUp(self):
        self.user = create_user()
        self.url = reverse(
            "password_confirm",
            args=[encode_uid(self.user), make_password_reset_token(self.user)],
        )

    def payload(self, new_password=NEW_PASSWORD, confirm_password=NEW_PASSWORD):
        return {"new_password": new_password, "confirm_password": confirm_password}

    def test_changes_password(self):
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data, {"detail": "Your Password has been successfully reset."}
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_link_can_only_be_used_once(self):
        self.client.post(self.url, self.payload(), format="json")

        response = self.client.post(
            self.url, self.payload("An0ther!Passw0rd", "An0ther!Passw0rd"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_mismatching_passwords(self):
        response = self.client.post(
            self.url, self.payload(confirm_password="Other!Passw0rd"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_rejects_invalid_token(self):
        url = reverse("password_confirm", args=[encode_uid(self.user), "invalid"])

        response = self.client.post(url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))
