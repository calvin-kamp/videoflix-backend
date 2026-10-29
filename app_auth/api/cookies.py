"""Helpers that put the JWTs into HttpOnly cookies."""

from django.conf import settings
from rest_framework_simplejwt.settings import api_settings


def _set_cookie(response, key, value, lifetime):
    response.set_cookie(
        key,
        value,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def set_access_cookie(response, access_token):
    """Store the access token in the ``access_token`` cookie."""
    _set_cookie(
        response,
        settings.AUTH_COOKIE_ACCESS,
        str(access_token),
        api_settings.ACCESS_TOKEN_LIFETIME,
    )


def set_refresh_cookie(response, refresh_token):
    """Store the refresh token in the ``refresh_token`` cookie."""
    _set_cookie(
        response,
        settings.AUTH_COOKIE_REFRESH,
        str(refresh_token),
        api_settings.REFRESH_TOKEN_LIFETIME,
    )


def delete_auth_cookies(response):
    """Remove both JWT cookies from the client."""
    for key in (settings.AUTH_COOKIE_ACCESS, settings.AUTH_COOKIE_REFRESH):
        response.delete_cookie(key, samesite=settings.AUTH_COOKIE_SAMESITE)
