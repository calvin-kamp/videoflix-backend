"""Models for the video app."""

from django.db import models


class Video(models.Model):
    """A movie that is streamed as HLS in several resolutions.

    After upload the RQ worker converts ``video_file`` into HLS playlists
    and segments under ``MEDIA_ROOT/hls/<id>/<resolution>/`` and creates a
    thumbnail if none was uploaded (see ``tasks.py``).
    """

    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to="thumbnails/", blank=True)
    video_file = models.FileField(upload_to="videos/")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
