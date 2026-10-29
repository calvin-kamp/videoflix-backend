"""Serializers for the video endpoints."""

from rest_framework import serializers

from app_video.models import Video


class VideoSerializer(serializers.ModelSerializer):
    """Metadata of a video for ``GET /api/video/``."""

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            "id",
            "created_at",
            "title",
            "description",
            "thumbnail_url",
            "category",
        ]

    def get_thumbnail_url(self, obj):
        if not obj.thumbnail:
            return None
        request = self.context.get("request")
        url = obj.thumbnail.url

        return request.build_absolute_uri(url) if request else url
