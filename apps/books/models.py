from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    isbn = models.CharField(max_length=13, unique=True, blank=True, null=True)
    publication_date = models.DateField()
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')
    available = models.BooleanField(default=True)
    copies_total = models.PositiveIntegerField(default=1)
    copies_available = models.PositiveIntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(fields=['isbn']),
            models.Index(fields=['genre']),
            models.Index(fields=['title', 'author']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(copies_available__lte=models.F('copies_total')),
                name='copies_available_lte_total',
            ),
            models.CheckConstraint(
                condition=models.Q(copies_available__gte=0),
                name='copies_available_gte_zero',
            ),
        ]

    def __str__(self):
        return self.title


class Rating(models.Model):
    rate = models.IntegerField(validators=[
        MinValueValidator(1),
        MaxValueValidator(100)
    ])
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings')
    review = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['book', 'rate']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['book', 'user'], name='unique_rating_per_user'),
        ]
