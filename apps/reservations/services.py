from django.db.models import QuerySet

from .models import Reservation


class ReservationRepository:
    """Encapsulates all Reservation data access logic."""

    @staticmethod
    def get_user_reservations(user) -> QuerySet:
        return (
            Reservation.objects.filter(user=user)
            .select_related("book", "user")
            .order_by("-reserved_at")
        )

    @staticmethod
    def get_by_id(reservation_id: int) -> Reservation:
        return Reservation.objects.select_related("book", "user").get(pk=reservation_id)

    @staticmethod
    def get_active_for_user_and_book(user, book) -> QuerySet:
        return Reservation.objects.filter(
            user=user,
            book=book,
            status=Reservation.Status.ACTIVE,
        )
