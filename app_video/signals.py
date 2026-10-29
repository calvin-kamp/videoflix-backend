"""Signal handlers that start the conversion and clean up files."""

import django_rq
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from . import services
from .models import Video
from .tasks import convert_video


@receiver(post_save, sender=Video)
def enqueue_video_conversion(sender, instance, created, **kwargs):
    """Enqueue the HLS conversion for newly uploaded videos.

    django-rq enqueues on transaction commit, so the worker never sees
    a video that is not saved yet.
    """
    if created and instance.video_file:
        django_rq.enqueue(convert_video, instance.pk)


@receiver(post_delete, sender=Video)
def delete_video_files(sender, instance, **kwargs):
    """Remove all files of a deleted video from disk."""
    services.delete_video_files(instance)
