from rest_framework import serializers
from .models import BookAnalytics


class BookAnalyticsSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)

    class Meta:
        model = BookAnalytics
        fields = [
            'book_id', 'book_title', 'avg_rating', 'total_ratings',
            'total_reservations', 'popularity_score', 'last_updated',
        ]
