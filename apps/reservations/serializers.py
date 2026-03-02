from rest_framework import serializers
from .models import Reservation


class ReservationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id', 'username', 'book', 'book_title',
            'reserved_at', 'due_date', 'returned_at', 'status',
        ]
        read_only_fields = ['id', 'username', 'book_title', 'reserved_at', 'returned_at', 'status']
