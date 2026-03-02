from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import BookAnalytics
from .serializers import BookAnalyticsSerializer


class TopBooksView(generics.ListAPIView):
    """CQRS read model: returns top books by popularity score."""
    serializer_class = BookAnalyticsSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return BookAnalytics.objects.select_related('book').order_by('-popularity_score')[:20]
