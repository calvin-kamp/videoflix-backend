"""Admin configuration for videos.

Uploading a video here starts the HLS conversion in the RQ worker.
"""

from django.contrib import admin

from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    """Admin for uploading and managing videos."""

    list_display = ("title", "category", "created_at")
    list_filter = ("category",)
    search_fields = ("title", "description")
