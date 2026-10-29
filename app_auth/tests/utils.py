"""Shared helpers for the auth tests."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()

PASSWORD = "Str0ng!Passw0rd"


def run_job_now(func, *args, **kwargs):
    """Stand-in for ``django_rq.enqueue`` that runs the job synchronously."""
    return func(*args, **kwargs)


def enqueue_synchronously(test_case):
    """Run RQ jobs of ``app_auth.services`` inline for the given test case.

    Sent emails then show up in ``django.core.mail.outbox``.
    """
    patcher = patch("app_auth.services.django_rq.enqueue", side_effect=run_job_now)
    mock = patcher.start()
    test_case.addCleanup(patcher.stop)
    return mock


def create_user(email="user@example.com", password=PASSWORD, is_active=True):
    """Create a user whose username is its email, like the registration does."""
    return User.objects.create_user(
        username=email, email=email, password=password, is_active=is_active
    )


def encode_uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def make_password_reset_token(user):
    return default_token_generator.make_token(user)
