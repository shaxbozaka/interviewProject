from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta

from .models import Reservation
from .serializers import ReservationSerializer


class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Reservation.objects.filter(
            user=self.request.user
        ).select_related('book', 'user')

    def perform_create(self, serializer):
        book = serializer.validated_data['book']
        if book.copies_available <= 0:
            raise ValidationError({'book': 'No copies available.'})
        book.copies_available -= 1
        book.save()
        serializer.save(
            user=self.request.user,
            status=Reservation.Status.ACTIVE,
            due_date=timezone.now() + timedelta(days=14),
        )

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        reservation = self.get_object()
        if reservation.status == Reservation.Status.RETURNED:
            return Response(
                {'detail': 'Book already returned.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reservation.status = Reservation.Status.RETURNED
        reservation.returned_at = timezone.now()
        reservation.save()
        reservation.book.copies_available += 1
        reservation.book.save()
        return Response(ReservationSerializer(reservation).data)
