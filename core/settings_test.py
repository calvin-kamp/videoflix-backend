"""
Test settings for core project.

Runs the test suite without PostgreSQL and Redis:

    python manage.py test --settings=core.settings_test
"""

import warnings

from .settings import *  # noqa: F401,F403

# STATIC_ROOT only exists after collectstatic, which tests don't need.
warnings.filterwarnings("ignore", message="No directory at")


# ------------------------------------------------------------------------------
# Database and cache
# ------------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


# ------------------------------------------------------------------------------
# Speed and isolation
# ------------------------------------------------------------------------------

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
