from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
    path('dashboard/recent-activity/', views.recent_activity, name='dashboard-recent-activity'),
    path('dashboard/cache-stats/', views.cache_stats, name='dashboard-cache-stats'),
    path('dashboard/system-info/', views.system_info, name='dashboard-system-info'),
    path('dashboard/k8s/', views.k8s_info, name='dashboard-k8s'),
    path('dashboard/traces/', views.request_traces, name='dashboard-traces'),
    path('dashboard/clear-cache/', views.clear_cache, name='dashboard-clear-cache'),
]
