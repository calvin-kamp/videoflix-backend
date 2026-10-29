"""Tests for ``GET /api/video/<movie_id>/<resolution>/<segment>/``."""

from django.urls import reverse
from rest_framework import status

from .utils import VideoAPITestCase, create_video, write_hls_file

SEGMENT = b"\x47\x40\x00\x10binary-ts-data"


class VideoSegmentTests(VideoAPITestCase):
    def setUp(self):
        super().setUp()
        self.video = create_video()
        write_hls_file(self.video, "480p", "000.ts", SEGMENT)

    def url(self, movie_id, resolution="480p", segment="000.ts"):
        return reverse("video-segment", args=[movie_id, resolution, segment])

    def test_returns_segment(self):
        response = self.client.get(self.url(self.video.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "video/MP2T")
        self.assertEqual(b"".join(response.streaming_content), SEGMENT)

    def test_works_without_trailing_slash(self):
        url = self.url(self.video.id).rstrip("/")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), SEGMENT)

    def test_missing_segment_returns_404(self):
        response = self.client.get(self.url(self.video.id, segment="999.ts"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_rejects_non_segment_files(self):
        write_hls_file(self.video, "480p", "secret.txt", b"secret")

        response = self.client.get(self.url(self.video.id, segment="secret.txt"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_rejects_path_traversal(self):
        response = self.client.get(
            f"/api/video/{self.video.id}/480p/..%2F..%2F..%2Fsettings.ts/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unknown_video_returns_404(self):
        response = self.client.get(self.url(self.video.id + 1))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_requires_authentication(self):
        self.logout()

        response = self.client.get(self.url(self.video.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
