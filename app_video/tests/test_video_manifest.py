"""Tests for ``GET /api/video/<movie_id>/<resolution>/index.m3u8``."""

from django.urls import reverse
from rest_framework import status

from .utils import VideoAPITestCase, create_video, write_hls_file

PLAYLIST = b"#EXTM3U\n#EXT-X-VERSION:3\n#EXTINF:10.0,\n000.ts\n#EXT-X-ENDLIST\n"


class VideoManifestTests(VideoAPITestCase):
    def setUp(self):
        super().setUp()
        self.video = create_video()
        write_hls_file(self.video, "720p", "index.m3u8", PLAYLIST)

    def url(self, movie_id, resolution="720p"):
        return reverse("video-manifest", args=[movie_id, resolution])

    def test_returns_playlist(self):
        response = self.client.get(self.url(self.video.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/vnd.apple.mpegurl")
        self.assertEqual(b"".join(response.streaming_content), PLAYLIST)

    def test_ignores_accept_header_of_players(self):
        response = self.client.get(
            self.url(self.video.id), HTTP_ACCEPT="application/vnd.apple.mpegurl"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unknown_video_returns_404(self):
        response = self.client.get(self.url(self.video.id + 1))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unsupported_resolution_returns_404(self):
        response = self.client.get(self.url(self.video.id, "4k"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_playlist_returns_404(self):
        response = self.client.get(self.url(self.video.id, "1080p"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_requires_authentication(self):
        self.logout()

        response = self.client.get(self.url(self.video.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
