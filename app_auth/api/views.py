"""Views for registration, activation, login, logout and password reset.

All views here are public. ``authentication_classes`` is emptied so an
expired ``access_token`` cookie can not block e.g. the login.
"""

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from app_auth import services

from .cookies import delete_auth_cookies, set_access_cookie, set_refresh_cookie
from .serializers import (
    LoginSerializer,
    PasswordConfirmSerializer,
    PasswordResetSerializer,
    RegistrationSerializer,
)


class PublicAPIView(APIView):
    """Base view without authentication and permission checks."""

    authentication_classes = []
    permission_classes = [AllowAny]


class RegisterView(PublicAPIView):
    """``POST /api/register/`` - create an inactive account."""

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, token = services.register_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        return Response(
            {"user": {"id": user.id, "email": user.email}, "token": token},
            status=status.HTTP_201_CREATED,
        )


class ActivateView(PublicAPIView):
    """``GET /api/activate/<uidb64>/<token>/`` - activate an account."""

    def get(self, request, uidb64, token):
        if not services.activate_user(uidb64, token):
            return Response(
                {"message": "Activation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"message": "Account successfully activated."})


class LoginView(PublicAPIView):
    """``POST /api/login/`` - set the JWT cookies."""

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                "detail": "Login successful",
                "user": {"id": user.id, "username": user.email},
            }
        )
        set_access_cookie(response, refresh.access_token)
        set_refresh_cookie(response, refresh)
        return response


class LogoutView(PublicAPIView):
    """``POST /api/logout/`` - blacklist the refresh token, delete cookies."""

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if raw_refresh is None:
            return Response(
                {"detail": "Refresh token missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            RefreshToken(raw_refresh).blacklist()
        except TokenError:
            response = Response(
                {"detail": "Refresh token invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            response = Response(
                {
                    "detail": "Logout successful! All tokens will be deleted. "
                    "Refresh token is now invalid."
                }
            )
        delete_auth_cookies(response)
        return response


class TokenRefreshView(PublicAPIView):
    """``POST /api/token/refresh/`` - issue a new access token cookie."""

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if raw_refresh is None:
            return Response(
                {"detail": "Refresh token missing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            access = RefreshToken(raw_refresh).access_token
        except TokenError:
            return Response(
                {"detail": "Refresh token invalid."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response = Response({"detail": "Token refreshed", "access": str(access)})
        set_access_cookie(response, access)
        return response


class PasswordResetView(PublicAPIView):
    """``POST /api/password_reset/`` - send a password reset link."""

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        services.request_password_reset(serializer.validated_data["email"])
        return Response(
            {"detail": "An email has been sent to reset your password."}
        )


class PasswordConfirmView(PublicAPIView):
    """``POST /api/password_confirm/<uidb64>/<token>/`` - set a new password."""

    def post(self, request, uidb64, token):
        serializer = PasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        changed = services.reset_password(
            uidb64, token, serializer.validated_data["new_password"]
        )
        if not changed:
            return Response(
                {"detail": "Password reset link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Your Password has been successfully reset."})
