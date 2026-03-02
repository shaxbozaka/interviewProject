from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.tracing import trace_step

from .commands import ReserveBookCommand, ReturnBookCommand, ExtendReservationCommand
from .serializers import ReservationSerializer
from .services import ReservationRepository


class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        return ReservationRepository.get_user_reservations(self.request.user)

    def perform_create(self, serializer):
        book = serializer.validated_data['book']
        trace_step(f'ReservationViewSet.perform_create() book={book.id} "{book.title}"', 'logic')
        command = ReserveBookCommand(user=self.request.user, book=book)
        reservation = command.execute()
        serializer.instance = reservation

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        reservation = self.get_object()
        trace_step(f'ReservationViewSet.return_book() reservation={reservation.id}', 'logic')
        command = ReturnBookCommand(reservation)
        result = command.execute()
        return Response(ReservationSerializer(result).data)

    @action(detail=True, methods=['post'])
    def extend(self, request, pk=None):
        reservation = self.get_object()
        days = int(request.data.get('days', 7))
        trace_step(f'ReservationViewSet.extend() reservation={reservation.id} +{days}d', 'logic')
        command = ExtendReservationCommand(reservation, extra_days=days)
        result = command.execute()
        return Response(ReservationSerializer(result).data)
