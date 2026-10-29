"""Shared helpers for the video tests."""

import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from app_video.models import Video
from app_video.services import get_hls_dir

User = get_user_model()


class VideoAPITestCase(APITestCase):
    """Test case with a temporary ``MEDIA_ROOT`` and an authenticated client."""

    def setUp(self):
        media_root = tempfile.mkdtemp(prefix="videoflix-test-")
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        media_override = override_settings(MEDIA_ROOT=media_root)
        media_override.enable()
        self.addCleanup(media_override.disable)

        self.user = User.objects.create_user(
            username="user@example.com", email="user@example.com", password="pw"
        )
        self.authenticate()

    def authenticate(self):
        """Log in the same way the frontend does: via the access cookie."""
        self.client.cookies["access_token"] = str(AccessToken.for_user(self.user))

    def logout(self):
        del self.client.cookies["access_token"]


def create_video(**fields):
    """Create a video without a file, so no conversion job is enqueued."""
    defaults = {"title": "Movie Title", "description": "Movie Description", "category": "Drama"}
    defaults.update(fields)
    return Video.objects.create(**defaults)


def write_hls_file(video, resolution, name, content):
    """Write a playlist or segment into the HLS directory of a video."""
    directory = get_hls_dir(video.pk, resolution)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(content)
