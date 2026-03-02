"""
Seed the database with sample data for development and demo.

Usage:
    python manage.py shell < scripts/seed.py
    OR
    python manage.py runscript seed (with django-extensions)
"""

import os
import sys
import random
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from apps.books.models import Book, Genre, Rating  # noqa: E402
from apps.analytics.consumers import update_book_analytics  # noqa: E402

User = get_user_model()

GENRES = [
    ("Fiction", "fiction"),
    ("Science Fiction", "science-fiction"),
    ("Fantasy", "fantasy"),
    ("Mystery", "mystery"),
    ("Non-Fiction", "non-fiction"),
    ("Biography", "biography"),
    ("Technology", "technology"),
    ("History", "history"),
    ("Philosophy", "philosophy"),
    ("Self-Help", "self-help"),
]

BOOKS = [
    ("Clean Code", "Robert C. Martin", "technology", "9780132350884"),
    ("Design Patterns", "Gang of Four", "technology", "9780201633610"),
    ("The Pragmatic Programmer", "David Thomas", "technology", "9780135957059"),
    ("Python Crash Course", "Eric Matthes", "technology", "9781593279288"),
    ("Django for Beginners", "William Vincent", "technology", "9781735467221"),
    (
        "Designing Data-Intensive Applications",
        "Martin Kleppmann",
        "technology",
        "9781449373320",
    ),
    ("System Design Interview", "Alex Xu", "technology", "9798664653403"),
    ("Harry Potter and the Sorcerer Stone", "J.K. Rowling", "fantasy", "9780590353427"),
    (
        "Harry Potter and the Chamber of Secrets",
        "J.K. Rowling",
        "fantasy",
        "9780439064873",
    ),
    ("The Hobbit", "J.R.R. Tolkien", "fantasy", "9780547928227"),
    ("Lord of the Rings", "J.R.R. Tolkien", "fantasy", "9780544003415"),
    ("Dune", "Frank Herbert", "science-fiction", "9780441172719"),
    ("Foundation", "Isaac Asimov", "science-fiction", "9780553293357"),
    ("Neuromancer", "William Gibson", "science-fiction", "9780441569595"),
    ("The Great Gatsby", "F. Scott Fitzgerald", "fiction", "9780743273565"),
    ("1984", "George Orwell", "fiction", "9780451524935"),
    ("To Kill a Mockingbird", "Harper Lee", "fiction", "9780060935467"),
    ("Brave New World", "Aldous Huxley", "fiction", "9780060850524"),
    ("Sapiens", "Yuval Noah Harari", "history", "9780062316097"),
    ("The Art of War", "Sun Tzu", "philosophy", "9781599869773"),
    ("Meditations", "Marcus Aurelius", "philosophy", "9780140449334"),
    ("Steve Jobs", "Walter Isaacson", "biography", "9781451648539"),
    ("Sherlock Holmes", "Arthur Conan Doyle", "mystery", "9780143122005"),
    ("Gone Girl", "Gillian Flynn", "mystery", "9780307588371"),
    ("Atomic Habits", "James Clear", "self-help", "9780735211292"),
]


def run():
    print("Seeding database...\n")

    # Create genres
    genres = {}
    for name, slug in GENRES:
        genre, created = Genre.objects.get_or_create(name=name, slug=slug)
        genres[slug] = genre
        if created:
            print(f"  Created genre: {name}")

    # Create users
    users = []
    admin, _ = User.objects.get_or_create(
        username="admin",
        defaults={"email": "admin@library.com", "role": "admin"},
    )
    if _:
        admin.set_password("admin123")
        admin.save()
        print("  Created admin user")
    users.append(admin)

    for i in range(1, 6):
        user, created = User.objects.get_or_create(
            username=f"member{i}",
            defaults={"email": f"member{i}@library.com", "role": "member"},
        )
        if created:
            user.set_password("member123")
            user.save()
            print(f"  Created user: member{i}")
        users.append(user)

    librarian, _ = User.objects.get_or_create(
        username="librarian",
        defaults={"email": "librarian@library.com", "role": "librarian"},
    )
    if _:
        librarian.set_password("librarian123")
        librarian.save()
        print("  Created librarian user")

    # Create books
    books = []
    for title, author, genre_slug, isbn in BOOKS:
        copies = random.randint(2, 10)
        book, created = Book.objects.get_or_create(
            isbn=isbn,
            defaults={
                "title": title,
                "author": author,
                "genre": genres[genre_slug],
                "publication_date": date(
                    random.randint(1990, 2024),
                    random.randint(1, 12),
                    random.randint(1, 28),
                ),
                "copies_total": copies,
                "copies_available": copies,
            },
        )
        if created:
            print(f"  Created book: {title}")
        books.append(book)

    # Create ratings
    rating_count = 0
    for user in users:
        sampled_books = random.sample(books, min(10, len(books)))
        for book in sampled_books:
            _, created = Rating.objects.get_or_create(
                book=book,
                user=user,
                defaults={
                    "rate": random.randint(40, 100),
                    "review": random.choice(
                        [
                            "Great book!",
                            "Highly recommended.",
                            "Interesting read.",
                            "Could be better.",
                            "A classic.",
                            "",
                        ]
                    ),
                },
            )
            if created:
                rating_count += 1
    print(f"  Created {rating_count} ratings")

    # Update analytics
    for book in books:
        update_book_analytics(book.id)
    print(f"  Updated analytics for {len(books)} books")

    print("\nSeed complete!")
    print(f"  Genres: {Genre.objects.count()}")
    print(f"  Users: {User.objects.count()}")
    print(f"  Books: {Book.objects.count()}")
    print(f"  Ratings: {Rating.objects.count()}")


if __name__ == "__main__":
    run()
