"""Tests for ``GET /api/video/``."""

from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

from .utils import VideoAPITestCase, create_video


class VideoListTests(VideoAPITestCase):
    url = reverse("video-list")

    def test_lists_videos_with_metadata(self):
        video = create_video(thumbnail="thumbnails/image.jpg")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(
            set(item),
            {"id", "created_at", "title", "description", "thumbnail_url", "category"},
        )
        self.assertEqual(item["id"], video.id)
        self.assertEqual(item["title"], "Movie Title")
        self.assertEqual(item["description"], "Movie Description")
        self.assertEqual(item["category"], "Drama")
        self.assertEqual(
            item["thumbnail_url"], "http://testserver/media/thumbnails/image.jpg"
        )

    def test_thumbnail_url_is_null_without_thumbnail(self):
        create_video()

        response = self.client.get(self.url)

        self.assertIsNone(response.data[0]["thumbnail_url"])

    def test_newest_video_comes_first(self):
        create_video(title="Old")
        create_video(title="New")

        response = self.client.get(self.url)

        self.assertEqual([item["title"] for item in response.data], ["New", "Old"])

    def test_accepts_bearer_header(self):
        self.logout()
        token = AccessToken.for_user(self.user)

        response = self.client.get(self.url, HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_requires_authentication(self):
        self.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rejects_invalid_access_cookie(self):
        self.client.cookies["access_token"] = "invalid"

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
