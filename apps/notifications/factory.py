from .strategies import (
    NotificationStrategy,
    EmailNotificationStrategy,
    InAppNotificationStrategy,
    PushNotificationStrategy,
)


class NotificationFactory:
    """
    Factory pattern: creates the appropriate notification strategy.

    Usage:
        strategy = NotificationFactory.create('email')
        strategy.send(user, 'Subject', 'Message')
    """

    _strategies: dict[str, type[NotificationStrategy]] = {
        "email": EmailNotificationStrategy,
        "in_app": InAppNotificationStrategy,
        "push": PushNotificationStrategy,
    }

    @classmethod
    def create(cls, channel: str) -> NotificationStrategy:
        strategy_class = cls._strategies.get(channel)
        if strategy_class is None:
            raise ValueError(f"Unknown notification channel: {channel}")
        return strategy_class()

    @classmethod
    def register(cls, channel: str, strategy_class: type[NotificationStrategy]):
        """Register a new notification channel (Open/Closed Principle)."""
        cls._strategies[channel] = strategy_class

    @classmethod
    def available_channels(cls) -> list[str]:
        return list(cls._strategies.keys())
