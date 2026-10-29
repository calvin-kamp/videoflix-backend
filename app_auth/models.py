"""Models for the auth app."""

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    """Manager for the custom user model."""

    def create_inactive_user(self, email, password):
        """Create a user that has to activate the account via email.

        The email doubles as username, so the superuser setup of
        ``backend.entrypoint.sh`` (which passes a username) keeps working.
        """
        email = self.normalize_email(email)

        return self.create_user(
            username=email, email=email, password=password, is_active=False
        )


class User(AbstractUser):
    """Videoflix user that logs in with email and password."""

    email = models.EmailField("email address", unique=True)

    objects = UserManager()
