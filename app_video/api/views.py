"""Views for the video list and HLS streaming."""

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.views import APIView

from app_video import services
from app_video.models import Video

from .serializers import VideoSerializer


class IgnoreClientContentNegotiation(BaseContentNegotiation):
    """Skip ``Accept`` header matching.

    Players request playlists and segments with media types DRF has no
    renderer for, which would otherwise end in ``406 Not Acceptable``.
    """

    def select_parser(self, request, parsers):
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


class VideoListView(ListAPIView):
    """``GET /api/video/`` - metadata of all videos."""

    queryset = Video.objects.all()
    serializer_class = VideoSerializer


class HLSFileView(APIView):
    """Base view that streams a file from the HLS directory of a video."""

    content_negotiation_class = IgnoreClientContentNegotiation
    content_type = None

    def file_response(self, movie_id, path):
        get_object_or_404(Video, pk=movie_id)

        if path is None:
            raise Http404("File not found.")

        return FileResponse(path.open("rb"), content_type=self.content_type)


class VideoManifestView(HLSFileView):
    """``GET /api/video/<movie_id>/<resolution>/index.m3u8`` - HLS playlist."""

    content_type = "application/vnd.apple.mpegurl"

    def get(self, request, movie_id, resolution):
        path = services.get_manifest_path(movie_id, resolution)
        return self.file_response(movie_id, path)


class VideoSegmentView(HLSFileView):
    """``GET /api/video/<movie_id>/<resolution>/<segment>/`` - HLS segment."""

    content_type = "video/MP2T"

    def get(self, request, movie_id, resolution, segment):
        path = services.get_segment_path(movie_id, resolution, segment)

        return self.file_response(movie_id, path)
