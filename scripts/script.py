from apps.books.models import Book, Rating

ratings = [
    {"rate": 5, "book_id": 1},
    {"rate": 2, "book_id": 1},
    {"rate": 3, "book_id": 1},
    {"rate": 1, "book_id": 2},
    {"rate": 2, "book_id": 2},
    {"rate": 5, "book_id": 3},
]
for x in ratings:
    rate = Rating(**x)
    rate.save()
