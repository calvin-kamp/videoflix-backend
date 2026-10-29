from django.apps import AppConfig


class AppVideoConfig(AppConfig):
    name = "app_video"

    def ready(self):
        from . import signals  # noqa: F401
