from django.db import models


class BookAnalytics(models.Model):
    """
    CQRS Read Model: denormalized analytics for books.
    Updated asynchronously via Kafka consumers, not on every write.
    Optimized for read-heavy analytics queries.
    """

    book = models.OneToOneField(
        "books.Book",
        on_delete=models.CASCADE,
        related_name="analytics",
        primary_key=True,
    )
    avg_rating = models.FloatField(default=0.0)
    total_ratings = models.PositiveIntegerField(default=0)
    total_reservations = models.PositiveIntegerField(default=0)
    popularity_score = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "book_analytics"
        verbose_name_plural = "book analytics"

    def calculate_popularity(self):
        """Popularity = (avg_rating * 0.7) + (total_reservations * 0.3)"""
        self.popularity_score = (self.avg_rating * 0.7) + (
            self.total_reservations * 0.3
        )

    def __str__(self):
        return f"Analytics for book {self.book_id}"


class AuditLog(models.Model):
    """
    Event sourcing lite: captures all mutations for replay/debugging.
    Partitioned by month in production (via PostgreSQL table partitioning).
    """

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"

    action = models.CharField(max_length=10, choices=Action.choices)
    entity_type = models.CharField(max_length=50)
    entity_id = models.PositiveIntegerField()
    user_id = models.PositiveIntegerField(null=True, blank=True)
    changes = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["user_id"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type}:{self.entity_id}"
