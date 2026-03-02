import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NotificationStrategy(ABC):
    """Base strategy for sending notifications."""

    @abstractmethod
    def send(self, recipient, subject: str, message: str) -> bool:
        pass


class EmailNotificationStrategy(NotificationStrategy):
    """Send notifications via email."""

    def send(self, recipient, subject: str, message: str) -> bool:
        from django.core.mail import send_mail
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=None,  # uses DEFAULT_FROM_EMAIL
                recipient_list=[recipient.email],
            )
            logger.info('Email sent to %s: %s', recipient.email, subject)
            return True
        except Exception as e:
            logger.error('Failed to send email to %s: %s', recipient.email, e)
            return False


class InAppNotificationStrategy(NotificationStrategy):
    """Store notifications in-app (log for now, will use DB later)."""

    def send(self, recipient, subject: str, message: str) -> bool:
        logger.info(
            'In-app notification for %s: [%s] %s',
            recipient.username, subject, message,
        )
        return True


class PushNotificationStrategy(NotificationStrategy):
    """Send push notifications (stub for learning purposes)."""

    def send(self, recipient, subject: str, message: str) -> bool:
        logger.info(
            'Push notification for %s: [%s] %s',
            recipient.username, subject, message,
        )
        return True
