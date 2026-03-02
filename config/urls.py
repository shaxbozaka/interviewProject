from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.books.urls')),
    path('api/v1/', include('apps.reservations.urls')),
    path('api/v1/', include('apps.analytics.urls')),
    path('api/v1/', include('apps.search.urls')),
    path('api/v1/users/', include('apps.users.urls')),
]
