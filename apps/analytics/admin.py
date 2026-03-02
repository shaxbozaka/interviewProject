from django.contrib import admin
from .models import BookAnalytics, AuditLog


@admin.register(BookAnalytics)
class BookAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['book', 'avg_rating', 'total_ratings', 'total_reservations', 'popularity_score']
    readonly_fields = ['book', 'avg_rating', 'total_ratings', 'total_reservations', 'popularity_score', 'last_updated']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'entity_type', 'entity_id', 'user_id', 'timestamp']
    list_filter = ['action', 'entity_type']
    readonly_fields = ['action', 'entity_type', 'entity_id', 'user_id', 'changes', 'timestamp']
