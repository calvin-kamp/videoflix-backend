"""Background jobs of the video app, executed by the RQ worker."""

from . import services
from .models import Video


def convert_video(video_id):
    """Convert an uploaded video to HLS.

    Takes the id instead of the instance, so the job always works on the
    current database state. Does nothing if the video was deleted meanwhile.
    """
    video = Video.objects.filter(pk=video_id).first()
    if video is None or not video.video_file:
        return

    services.process_video(video)
