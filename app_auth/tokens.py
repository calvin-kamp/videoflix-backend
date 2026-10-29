"""Tokens for account activation links."""

from django.contrib.auth.tokens import PasswordResetTokenGenerator


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    """Token generator whose tokens become invalid once the account is active."""

    key_salt = "app_auth.tokens.AccountActivationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.is_active}{timestamp}"


account_activation_token = AccountActivationTokenGenerator()
