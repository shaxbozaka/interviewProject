from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# Write a Django model for Book with fields: title, author, publication_date, and an available flag (boolean).

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=50)
    publication_date = models.DateField()
    available = models.BooleanField(default=True)


class Rating(models.Model):
    rate = models.IntegerField(validators=[
            MinValueValidator(1),
            MaxValueValidator(100)
        ])
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='ratings')

    class Meta:
        indexes = [
            models.Index(fields=['book', 'rate']),
        ]
