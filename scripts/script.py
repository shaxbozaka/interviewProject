from apps.books.models import Book, Rating

# val = Book.objects.all()
# # x.save()
# for x in val:
#     print(x)


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