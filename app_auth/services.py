"""Business logic of the auth app.

Views stay thin and call into this module. Emails are not sent here
directly but enqueued for the RQ worker (see ``tasks.py``).
"""

import django_rq
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .tasks import send_templated_email
from .tokens import account_activation_token

User = get_user_model()


def encode_uid(user):
    """Return the base64-encoded primary key used in email links."""
    return urlsafe_base64_encode(force_bytes(user.pk))


def get_user_by_uidb64(uidb64):
    """Return the user for a base64-encoded primary key, or ``None``."""
    try:
        pk = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=pk)

    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


def build_frontend_link(path, user, token):
    """Build a frontend URL that carries ``uid`` and ``token`` as query params."""
    base_url = settings.FRONTEND_URL.rstrip("/")

    return f"{base_url}/{path.lstrip('/')}?uid={encode_uid(user)}&token={token}"


def register_user(email, password):
    """Create an inactive user and send the activation email.

    Returns:
        Tuple of the new user and the activation token.
    """
    user = User.objects.create_inactive_user(email=email, password=password)
    token = account_activation_token.make_token(user)
    send_activation_email(user, token)

    return user, token


def send_activation_email(user, token):
    """Enqueue the email with the account activation link."""
    activation_url = build_frontend_link(settings.FRONTEND_ACTIVATION_PATH, user, token)
    django_rq.enqueue(
        send_templated_email,
        subject="Confirm your email",
        template_name="activation",
        context={"email": user.email, "activation_url": activation_url},
        recipient=user.email,
    )


def activate_user(uidb64, token):
    """Activate the account if the token is valid.

    Returns:
        ``True`` if the account was activated, ``False`` otherwise.
    """
    user = get_user_by_uidb64(uidb64)
    if user is None or not account_activation_token.check_token(user, token):
        return False

    user.is_active = True
    user.save(update_fields=["is_active"])

    return True


def request_password_reset(email):
    """Enqueue a password reset email if a user with this email exists.

    Does nothing for unknown addresses, so the response can not be used
    to find out which emails are registered.
    """
    user = User.objects.filter(email__iexact=email).first()

    if user is None:
        return

    token = default_token_generator.make_token(user)
    reset_url = build_frontend_link(settings.FRONTEND_PASSWORD_RESET_PATH, user, token)
    django_rq.enqueue(
        send_templated_email,
        subject="Reset your password",
        template_name="password_reset",
        context={"email": user.email, "reset_url": reset_url},
        recipient=user.email,
    )


def reset_password(uidb64, token, new_password):
    """Set a new password if the reset token is valid.

    The token becomes invalid afterwards, because it is bound to the
    password hash.

    Returns:
        ``True`` if the password was changed, ``False`` otherwise.
    """
    user = get_user_by_uidb64(uidb64)

    if user is None or not default_token_generator.check_token(user, token):
        return False

    user.set_password(new_password)
    user.save(update_fields=["password"])

    return True
