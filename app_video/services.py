"""Business logic of the video app: ffmpeg conversion and HLS file lookup."""

import re
import shutil
import subprocess
from pathlib import Path

from django.conf import settings

MANIFEST_NAME = "index.m3u8"
THUMBNAIL_DIR = "thumbnails"
SEGMENT_PATTERN = re.compile(r"^[\w-]+\.ts$")


def get_hls_dir(video_id, resolution=None):
    """Return the HLS directory of a video, or of one of its resolutions."""
    hls_dir = Path(settings.MEDIA_ROOT) / "hls" / str(video_id)

    return hls_dir / resolution if resolution else hls_dir


def get_manifest_path(video_id, resolution):
    """Return the path of an existing playlist, or ``None``."""
    if resolution not in settings.VIDEO_RESOLUTIONS:
        return None
    path = get_hls_dir(video_id, resolution) / MANIFEST_NAME

    return path if path.is_file() else None


def get_segment_path(video_id, resolution, segment):
    """Return the path of an existing ``.ts`` segment, or ``None``.

    The segment name is matched against ``SEGMENT_PATTERN`` so it can not
    point outside of the HLS directory.
    """
    if resolution not in settings.VIDEO_RESOLUTIONS:
        return None
    if not SEGMENT_PATTERN.match(segment):
        return None
    path = get_hls_dir(video_id, resolution) / segment

    return path if path.is_file() else None


def run_ffmpeg(arguments):
    """Run ffmpeg with the given arguments; raises on a non-zero exit code."""
    subprocess.run(
        [settings.FFMPEG_BINARY, "-y", *arguments],
        check=True,
        capture_output=True,
    )


def convert_to_hls(source, output_dir, height):
    """Encode ``source`` as HLS with the given frame height.

    Writes ``index.m3u8`` and the segments ``000.ts``, ``001.ts``, ... into
    ``output_dir``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-i",
            str(source),
            "-vf",
            f"scale=-2:{height}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-f",
            "hls",
            "-hls_time",
            "10",
            "-hls_playlist_type",
            "vod",
            "-hls_segment_filename",
            str(output_dir / "%03d.ts"),
            str(output_dir / MANIFEST_NAME),
        ]
    )


def create_thumbnail(video):
    """Grab a frame of the video and store it as the video's thumbnail."""
    relative_path = f"{THUMBNAIL_DIR}/video_{video.pk}.jpg"
    target = Path(settings.MEDIA_ROOT) / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-ss",
            "00:00:01",
            "-i",
            video.video_file.path,
            "-frames:v",
            "1",
            "-vf",
            "scale=-2:720",
            str(target),
        ]
    )
    video.thumbnail.name = relative_path
    video.save(update_fields=["thumbnail"])


def process_video(video):
    """Create all HLS resolutions and, if missing, the thumbnail."""
    for resolution, height in settings.VIDEO_RESOLUTIONS.items():
        convert_to_hls(video.video_file.path, get_hls_dir(video.pk, resolution), height)

    if not video.thumbnail:
        create_thumbnail(video)


def delete_video_files(video):
    """Remove the uploaded file, the thumbnail and all HLS files of a video."""
    if video.video_file:
        video.video_file.delete(save=False)

    if video.thumbnail:
        video.thumbnail.delete(save=False)

    shutil.rmtree(get_hls_dir(video.pk), ignore_errors=True)
