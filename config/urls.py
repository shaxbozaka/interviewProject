from django.contrib import admin
from django.urls import include, path

from apps.dashboard.views import DashboardView, FrontendView
from core.health import health_check

urlpatterns = [
    path("", FrontendView.as_view(), name="frontend"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("api/v1/", include("apps.dashboard.urls")),
    path("api/v1/", include("apps.books.urls")),
    path("api/v1/", include("apps.reservations.urls")),
    path("api/v1/", include("apps.analytics.urls")),
    path("api/v1/", include("apps.search.urls")),
    path("api/v1/users/", include("apps.users.urls")),
]
