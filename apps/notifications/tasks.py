import logging

from celery import shared_task
from django.contrib.auth import get_user_model

from .factory import NotificationFactory

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_reservation_confirmation(self, user_id: int, book_title: str):
    """Send confirmation when a book is reserved."""
    try:
        user = User.objects.get(pk=user_id)
        strategy = NotificationFactory.create('email')
        strategy.send(
            recipient=user,
            subject='Reservation Confirmed',
            message=f'You have successfully reserved "{book_title}". '
                    f'Please return it within 14 days.',
        )
        logger.info('Reservation confirmation sent to user %d', user_id)
    except User.DoesNotExist:
        logger.error('User %d not found for reservation confirmation', user_id)
    except Exception as exc:
        logger.error('Failed to send reservation confirmation: %s', exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_return_confirmation(self, user_id: int, book_title: str):
    """Send confirmation when a book is returned."""
    try:
        user = User.objects.get(pk=user_id)
        strategy = NotificationFactory.create('email')
        strategy.send(
            recipient=user,
            subject='Book Returned',
            message=f'You have returned "{book_title}". Thank you!',
        )
    except User.DoesNotExist:
        logger.error('User %d not found for return confirmation', user_id)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def check_overdue_reservations():
    """
    Periodic task: find overdue reservations and notify users.
    Meant to be run by Celery Beat (e.g., every hour).
    """
    from django.utils import timezone
    from apps.reservations.models import Reservation

    overdue = Reservation.objects.filter(
        status=Reservation.Status.ACTIVE,
        due_date__lt=timezone.now(),
    ).select_related('user', 'book')

    for reservation in overdue:
        reservation.status = Reservation.Status.OVERDUE
        reservation.save()

        strategy = NotificationFactory.create('email')
        strategy.send(
            recipient=reservation.user,
            subject='Book Overdue',
            message=f'Your reservation for "{reservation.book.title}" is overdue. '
                    f'Please return it as soon as possible.',
        )

    logger.info('Checked overdue reservations: %d found', overdue.count())
