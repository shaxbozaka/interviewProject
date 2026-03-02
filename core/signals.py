import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def user_activity_event(sender, instance, created, **kwargs):
    """Publish user creation events to Kafka."""
    if created:
        from core.events import publish_event

        publish_event(
            topic="user-events",
            event_type="user.created",
            data={"user_id": instance.id, "username": instance.username},
            key=str(instance.id),
        )
