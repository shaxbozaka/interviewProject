from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"
    label = "analytics"

    def ready(self):
        import core.signals  # noqa: F401 — register signal handlers
