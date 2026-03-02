"""
Massive data seeder — populates the database with realistic library data.

Generates:
  - 25 genres
  - 500 users (admins, librarians, members)
  - 5,000 books with realistic titles, ISBNs, and metadata
  - 50,000 ratings with reviews
  - 10,000 reservations (active, returned, overdue)
  - Full analytics recalculation

Usage:
    docker compose exec web python scripts/seed_massive.py

Designed for bulk_create with batch processing for memory efficiency.
"""
import os
import sys
import random
import time
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.books.models import Book, Genre, Rating
from apps.reservations.models import Reservation
from apps.analytics.models import BookAnalytics, AuditLog

User = get_user_model()

# ---------------------------------------------------------------------------
# Realistic data pools
# ---------------------------------------------------------------------------
GENRES = [
    ('Fiction', 'fiction'), ('Science Fiction', 'science-fiction'),
    ('Fantasy', 'fantasy'), ('Mystery', 'mystery'),
    ('Thriller', 'thriller'), ('Romance', 'romance'),
    ('Horror', 'horror'), ('Non-Fiction', 'non-fiction'),
    ('Biography', 'biography'), ('Autobiography', 'autobiography'),
    ('Technology', 'technology'), ('Computer Science', 'computer-science'),
    ('History', 'history'), ('Philosophy', 'philosophy'),
    ('Psychology', 'psychology'), ('Self-Help', 'self-help'),
    ('Business', 'business'), ('Economics', 'economics'),
    ('Science', 'science'), ('Mathematics', 'mathematics'),
    ('Poetry', 'poetry'), ('Drama', 'drama'),
    ('Children', 'children'), ('Young Adult', 'young-adult'),
    ('Art & Design', 'art-design'),
]

FIRST_NAMES = [
    'James', 'Mary', 'Robert', 'Patricia', 'John', 'Jennifer', 'Michael',
    'Linda', 'David', 'Elizabeth', 'William', 'Barbara', 'Richard', 'Susan',
    'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Christopher', 'Karen', 'Charles',
    'Lisa', 'Daniel', 'Nancy', 'Matthew', 'Betty', 'Anthony', 'Margaret',
    'Mark', 'Sandra', 'Donald', 'Ashley', 'Steven', 'Kimberly', 'Paul',
    'Emily', 'Andrew', 'Donna', 'Joshua', 'Michelle', 'Kenneth', 'Dorothy',
    'Kevin', 'Carol', 'Brian', 'Amanda', 'George', 'Melissa', 'Timothy',
    'Deborah', 'Ronald', 'Stephanie', 'Edward', 'Rebecca', 'Jason', 'Sharon',
    'Jeffrey', 'Laura', 'Ryan', 'Cynthia', 'Jacob', 'Kathleen', 'Gary',
    'Amy', 'Nicholas', 'Angela', 'Eric', 'Shirley', 'Jonathan', 'Anna',
    'Stephen', 'Brenda', 'Larry', 'Pamela', 'Justin', 'Emma', 'Scott',
    'Nicole', 'Brandon', 'Helen', 'Benjamin', 'Samantha', 'Samuel', 'Katherine',
    'Raymond', 'Christine', 'Gregory', 'Debra', 'Frank', 'Rachel', 'Alexander',
    'Carolyn', 'Patrick', 'Janet', 'Jack', 'Catherine', 'Dennis', 'Maria',
    'Jerry', 'Heather', 'Tyler', 'Diane',
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller',
    'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez',
    'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
    'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark',
    'Ramirez', 'Lewis', 'Robinson', 'Walker', 'Young', 'Allen', 'King',
    'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores', 'Green',
    'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell', 'Mitchell',
    'Carter', 'Roberts', 'Gomez', 'Phillips', 'Evans', 'Turner', 'Diaz',
    'Parker', 'Cruz', 'Edwards', 'Collins', 'Reyes', 'Stewart', 'Morris',
    'Morales', 'Murphy', 'Cook', 'Rogers', 'Gutierrez', 'Ortiz', 'Morgan',
    'Cooper', 'Peterson', 'Bailey', 'Reed', 'Kelly', 'Howard', 'Ramos',
    'Kim', 'Cox', 'Ward', 'Richardson', 'Watson', 'Brooks', 'Chavez',
    'Wood', 'James', 'Bennett', 'Gray', 'Mendoza', 'Ruiz', 'Hughes',
    'Price', 'Alvarez', 'Castillo', 'Sanders', 'Patel', 'Myers', 'Long',
    'Ross', 'Foster', 'Jimenez', 'Powell',
]

BOOK_PREFIXES = [
    'The', 'A', 'An', 'Introduction to', 'Advanced', 'Mastering',
    'Learning', 'Understanding', 'Exploring', 'The Art of', 'The Science of',
    'Practical', 'Modern', 'Essential', 'Complete Guide to', 'Fundamentals of',
    'Secrets of', 'Journey Through', 'Tales of', 'Chronicles of',
]

BOOK_SUBJECTS = [
    'Algorithms', 'Data Structures', 'Machine Learning', 'Deep Learning',
    'Web Development', 'Cloud Computing', 'Distributed Systems', 'Databases',
    'Operating Systems', 'Computer Networks', 'Cybersecurity', 'Blockchain',
    'Quantum Computing', 'Artificial Intelligence', 'Natural Language Processing',
    'Software Architecture', 'Design Patterns', 'Clean Code', 'DevOps',
    'Kubernetes', 'Docker', 'Microservices', 'System Design', 'API Design',
    'Python Programming', 'JavaScript Mastery', 'Rust Programming', 'Go Development',
    'Java Enterprise', 'C++ Performance', 'TypeScript', 'React Patterns',
    'Django Framework', 'Node.js', 'PostgreSQL', 'Redis Internals',
    'Kafka Streaming', 'Elasticsearch', 'GraphQL', 'gRPC',
    'the Dark Forest', 'the Lost Kingdom', 'the Shadow Realm', 'Forgotten Lands',
    'the Digital Age', 'the Renaissance', 'the Modern World', 'Ancient Civilizations',
    'the Human Mind', 'the Universe', 'Evolution', 'Consciousness',
    'Wall Street', 'Silicon Valley', 'the Startup World', 'Leadership',
    'Creative Thinking', 'Mindfulness', 'Productivity', 'Habit Formation',
    'the Civil War', 'World War II', 'the Cold War', 'the Space Race',
    'Rome', 'Greece', 'Egypt', 'Medieval Europe', 'the Samurai',
    'Relativity', 'Genetics', 'Astronomy', 'Chemistry',
    'Poetry Writing', 'Storytelling', 'Creative Writing', 'the Novel',
    'Painting', 'Photography', 'Sculpture', 'Architecture',
    'Love and Loss', 'Mystery Manor', 'the Detective', 'Night Watch',
    'Dragon Fire', 'the Wizard Tower', 'Elven Kingdoms', 'Dwarven Mines',
    'the Cosmos', 'Mars Colony', 'the Singularity', 'Time Travel',
    'Serial Killers', 'Cold Cases', 'the Missing', 'Forensic Science',
]

REVIEWS = [
    "Absolutely brilliant — one of the best books I've read this year.",
    "Couldn't put it down. Finished it in two sittings.",
    "A must-read for anyone interested in this topic.",
    "Well-written and thoroughly researched. Highly recommended.",
    "Changed my perspective completely. Eye-opening material.",
    "Good content but could use better organization in places.",
    "Solid introduction to the subject. Great for beginners.",
    "The examples are incredibly practical and easy to follow.",
    "A bit dense in parts, but worth the effort.",
    "This should be required reading in every university.",
    "The author has a gift for making complex topics accessible.",
    "Not what I expected, but pleasantly surprised.",
    "Some chapters are stronger than others, but overall good.",
    "Perfect companion for the course I'm taking.",
    "I've recommended this to all my colleagues.",
    "A classic that stands the test of time.",
    "Beautifully written. The prose is as good as the content.",
    "Practical, insightful, and thoroughly enjoyable.",
    "I wish I had read this 10 years ago.",
    "The best technical book I've ever read. Period.",
    "A page-turner from start to finish.",
    "Thought-provoking and deeply moving.",
    "The illustrations and diagrams are extremely helpful.",
    "A bit outdated in some areas, but the core concepts hold.",
    "Every developer should have this on their shelf.",
    "Engaging writing style. Makes learning fun.",
    "I learned more from this book than from my entire degree.",
    "The case studies are particularly valuable.",
    "Concise and to the point. No fluff.",
    "A masterpiece of technical writing.",
    "",  # Some ratings have no review
    "",
    "",
    "",
    "",
]

PUBLISHER_DOMAINS = [
    'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
    'library.org', 'university.edu', 'readers.club',
]


def generate_isbn():
    """Generate a unique 13-digit ISBN."""
    prefix = '978'
    body = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    isbn = prefix + body
    # Calculate check digit
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(isbn))
    check = (10 - (total % 10)) % 10
    return isbn + str(check)


def generate_book_title():
    """Generate a realistic book title."""
    prefix = random.choice(BOOK_PREFIXES)
    subject = random.choice(BOOK_SUBJECTS)
    return f'{prefix} {subject}'


def timer(label):
    """Simple timer context manager."""
    class Timer:
        def __enter__(self):
            self.start = time.time()
            return self
        def __exit__(self, *args):
            elapsed = time.time() - self.start
            print(f'  {label}: {elapsed:.2f}s')
    return Timer()


def run():
    start = time.time()
    print('=' * 60)
    print('  MASSIVE DATA SEEDER')
    print('=' * 60)
    print()

    # Configuration
    NUM_USERS = 500
    NUM_BOOKS = 5000
    NUM_RATINGS = 50000
    NUM_RESERVATIONS = 10000
    NUM_AUDIT_LOGS = 20000
    BATCH_SIZE = 1000

    # -----------------------------------------------------------------------
    # 1. Genres
    # -----------------------------------------------------------------------
    print(f'[1/7] Creating {len(GENRES)} genres...')
    with timer('Genres'):
        genres = []
        for name, slug in GENRES:
            genre, _ = Genre.objects.get_or_create(name=name, slug=slug)
            genres.append(genre)
    print(f'  Total genres: {Genre.objects.count()}')
    print()

    # -----------------------------------------------------------------------
    # 2. Users (bulk_create)
    # -----------------------------------------------------------------------
    print(f'[2/7] Creating {NUM_USERS} users...')
    with timer('Users'):
        existing_usernames = set(User.objects.values_list('username', flat=True))

        # Special users
        for uname, role, pwd in [
            ('admin', 'admin', 'admin123'),
            ('librarian', 'librarian', 'librarian123'),
            ('head_librarian', 'librarian', 'librarian123'),
        ]:
            if uname not in existing_usernames:
                u = User(username=uname, email=f'{uname}@library.com', role=role)
                u.set_password(pwd)
                u.save()
                existing_usernames.add(uname)

        # Bulk member users
        users_to_create = []
        for i in range(NUM_USERS):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            username = f'{first.lower()}.{last.lower()}.{i}'
            if username in existing_usernames:
                continue
            existing_usernames.add(username)
            domain = random.choice(PUBLISHER_DOMAINS)
            user = User(
                username=username,
                email=f'{username}@{domain}',
                first_name=first,
                last_name=last,
                role=random.choices(['member', 'librarian'], weights=[95, 5])[0],
                is_active=True,
            )
            user.set_password('member123')
            users_to_create.append(user)

        for i in range(0, len(users_to_create), BATCH_SIZE):
            User.objects.bulk_create(users_to_create[i:i + BATCH_SIZE], ignore_conflicts=True)

    all_users = list(User.objects.all())
    print(f'  Total users: {len(all_users)}')
    print()

    # -----------------------------------------------------------------------
    # 3. Books (bulk_create)
    # -----------------------------------------------------------------------
    print(f'[3/7] Creating {NUM_BOOKS} books...')
    with timer('Books'):
        existing_isbns = set(Book.objects.values_list('isbn', flat=True))
        used_isbns = set()
        books_to_create = []

        for _ in range(NUM_BOOKS):
            isbn = generate_isbn()
            while isbn in existing_isbns or isbn in used_isbns:
                isbn = generate_isbn()
            used_isbns.add(isbn)

            title = generate_book_title()
            author = f'{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}'
            copies = random.randint(1, 25)
            copies_available = random.randint(0, copies)

            books_to_create.append(Book(
                title=title,
                author=author,
                isbn=isbn,
                genre=random.choice(genres),
                publication_date=date(
                    random.randint(1950, 2025),
                    random.randint(1, 12),
                    random.randint(1, 28),
                ),
                copies_total=copies,
                copies_available=copies_available,
                available=copies_available > 0,
            ))

        for i in range(0, len(books_to_create), BATCH_SIZE):
            Book.objects.bulk_create(books_to_create[i:i + BATCH_SIZE], ignore_conflicts=True)

    all_books = list(Book.objects.all())
    book_ids = [b.id for b in all_books]
    user_ids = [u.id for u in all_users]
    print(f'  Total books: {len(all_books)}')
    print()

    # -----------------------------------------------------------------------
    # 4. Ratings (bulk_create with deduplication)
    # -----------------------------------------------------------------------
    print(f'[4/7] Creating {NUM_RATINGS} ratings...')
    with timer('Ratings'):
        existing_pairs = set(
            Rating.objects.values_list('book_id', 'user_id')
        )
        ratings_to_create = []
        attempts = 0

        while len(ratings_to_create) < NUM_RATINGS and attempts < NUM_RATINGS * 3:
            attempts += 1
            book_id = random.choice(book_ids)
            user_id = random.choice(user_ids)
            pair = (book_id, user_id)
            if pair in existing_pairs:
                continue
            existing_pairs.add(pair)

            ratings_to_create.append(Rating(
                book_id=book_id,
                user_id=user_id,
                rate=random.randint(1, 100),
                review=random.choice(REVIEWS),
            ))

        for i in range(0, len(ratings_to_create), BATCH_SIZE):
            Rating.objects.bulk_create(ratings_to_create[i:i + BATCH_SIZE], ignore_conflicts=True)

    print(f'  Total ratings: {Rating.objects.count()}')
    print()

    # -----------------------------------------------------------------------
    # 5. Reservations (bulk_create with realistic history)
    # -----------------------------------------------------------------------
    print(f'[5/7] Creating {NUM_RESERVATIONS} reservations...')
    with timer('Reservations'):
        now = timezone.now()
        reservations_to_create = []

        for _ in range(NUM_RESERVATIONS):
            days_ago = random.randint(0, 365)
            reserved_at = now - timedelta(days=days_ago)
            duration = random.randint(7, 30)
            due_date = reserved_at + timedelta(days=duration)

            # Determine status based on dates
            if days_ago < 14:
                status = random.choices(
                    ['active', 'returned', 'pending'],
                    weights=[50, 30, 20],
                )[0]
            elif due_date < now:
                status = random.choices(
                    ['returned', 'overdue'],
                    weights=[85, 15],
                )[0]
            else:
                status = 'returned'

            returned_at = None
            if status == 'returned':
                return_days = random.randint(1, duration + 5)
                returned_at = reserved_at + timedelta(days=return_days)

            reservations_to_create.append(Reservation(
                user_id=random.choice(user_ids),
                book_id=random.choice(book_ids),
                reserved_at=reserved_at,
                due_date=due_date,
                returned_at=returned_at,
                status=status,
            ))

        for i in range(0, len(reservations_to_create), BATCH_SIZE):
            Reservation.objects.bulk_create(reservations_to_create[i:i + BATCH_SIZE])

    print(f'  Total reservations: {Reservation.objects.count()}')
    print()

    # -----------------------------------------------------------------------
    # 6. Audit Logs (bulk_create)
    # -----------------------------------------------------------------------
    print(f'[6/7] Creating {NUM_AUDIT_LOGS} audit log entries...')
    with timer('Audit logs'):
        logs_to_create = []
        actions = ['create', 'update', 'delete']
        entities = ['book', 'rating', 'reservation', 'user']

        for _ in range(NUM_AUDIT_LOGS):
            action = random.choice(actions)
            entity = random.choice(entities)
            days_ago = random.randint(0, 365)

            logs_to_create.append(AuditLog(
                action=action,
                entity_type=entity,
                entity_id=random.randint(1, 5000),
                user_id=random.choice(user_ids),
                changes={'field': 'value', 'old': 'x', 'new': 'y'},
            ))

        for i in range(0, len(logs_to_create), BATCH_SIZE):
            AuditLog.objects.bulk_create(logs_to_create[i:i + BATCH_SIZE])

    print(f'  Total audit logs: {AuditLog.objects.count()}')
    print()

    # -----------------------------------------------------------------------
    # 7. Analytics (recalculate all)
    # -----------------------------------------------------------------------
    print(f'[7/7] Recalculating analytics for {len(all_books)} books...')
    with timer('Analytics'):
        from django.db.models import Avg, Count
        analytics_to_create = []

        for book in all_books:
            rating_data = Rating.objects.filter(book=book).aggregate(
                avg=Avg('rate'), count=Count('id'),
            )
            reservation_count = Reservation.objects.filter(book=book).count()
            avg_rating = rating_data['avg'] or 0.0
            total_ratings = rating_data['count']
            popularity = (avg_rating * 0.7) + (reservation_count * 0.3)

            analytics_to_create.append(BookAnalytics(
                book=book,
                avg_rating=avg_rating,
                total_ratings=total_ratings,
                total_reservations=reservation_count,
                popularity_score=popularity,
            ))

        # Delete existing and bulk create (faster than update_or_create)
        BookAnalytics.objects.all().delete()
        for i in range(0, len(analytics_to_create), BATCH_SIZE):
            BookAnalytics.objects.bulk_create(analytics_to_create[i:i + BATCH_SIZE])

    print(f'  Total analytics: {BookAnalytics.objects.count()}')
    print()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    elapsed = time.time() - start
    print('=' * 60)
    print('  SEED COMPLETE')
    print('=' * 60)
    print(f'''
  Genres:        {Genre.objects.count():>8,}
  Users:         {User.objects.count():>8,}
  Books:         {Book.objects.count():>8,}
  Ratings:       {Rating.objects.count():>8,}
  Reservations:  {Reservation.objects.count():>8,}
  Audit Logs:    {AuditLog.objects.count():>8,}
  Analytics:     {BookAnalytics.objects.count():>8,}

  Total records: {
    Genre.objects.count() + User.objects.count() + Book.objects.count() +
    Rating.objects.count() + Reservation.objects.count() +
    AuditLog.objects.count() + BookAnalytics.objects.count():>8,}

  Time elapsed:  {elapsed:>7.1f}s
''')


if __name__ == '__main__':
    run()
