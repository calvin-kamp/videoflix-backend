"""Serializers for the auth endpoints."""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()

INVALID_INPUT_MESSAGE = "Please check your input and try again."


class RegistrationSerializer(serializers.Serializer):
    """Validates the data for ``POST /api/register/``."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirmed_password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(INVALID_INPUT_MESSAGE)

        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirmed_password"]:
            raise serializers.ValidationError(
                {"confirmed_password": "Passwords do not match."}
            )
        validate_password(attrs["password"], User(email=attrs["email"]))

        return attrs


class LoginSerializer(serializers.Serializer):
    """Checks the credentials for ``POST /api/login/``.

    The validated data contains the authenticated ``user``. Inactive
    users are rejected by Django's ``ModelBackend``.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = User.objects.filter(email__iexact=attrs["email"]).first()
        if user is not None:
            user = authenticate(
                self.context.get("request"),
                username=user.username,
                password=attrs["password"],
            )

        if user is None:
            raise serializers.ValidationError(INVALID_INPUT_MESSAGE)

        update_last_login(None, user)
        attrs["user"] = user

        return attrs


class PasswordResetSerializer(serializers.Serializer):
    """Validates the data for ``POST /api/password_reset/``."""

    email = serializers.EmailField()


class PasswordConfirmSerializer(serializers.Serializer):
    """Validates the data for ``POST /api/password_confirm/<uidb64>/<token>/``."""

    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        validate_password(attrs["new_password"])

        return attrs
