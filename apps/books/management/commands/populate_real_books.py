"""
Fetch real book data from Open Library and update existing Book records.
Uses the subjects endpoint for popular books, then fetches descriptions
from individual work pages. Stores read URLs for readable books.
"""

import random
import time
import urllib.request
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from django.core.management.base import BaseCommand
from django.db import IntegrityError
from apps.books.models import Book, Genre


GENRE_SUBJECTS = {
    'fiction': 'fiction',
    'mystery': 'mystery',
    'science': 'science',
    'science-fiction': 'science_fiction',
    'romance': 'romance',
    'history': 'history',
    'fantasy': 'fantasy',
    'thriller': 'thriller',
    'biography': 'biography',
    'horror': 'horror',
    'poetry': 'poetry',
    'philosophy': 'philosophy',
    'children': 'children',
    'drama': 'drama',
    'non-fiction': 'nonfiction',
    'psychology': 'psychology',
    'economics': 'economics',
    'business': 'business',
    'technology': 'technology',
    'computer-science': 'computer_science',
    'mathematics': 'mathematics',
    'self-help': 'self-help',
    'art-design': 'art',
    'autobiography': 'autobiography',
    'young-adult': 'young_adult_fiction',
}


def ol_get(url, timeout=20):
    """GET from Open Library with retries."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'LibraryApp/1.0'})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except Exception:
            if attempt < 2:
                time.sleep(1)
    return None


def fetch_description(work_key):
    """Fetch description from a work page. Returns (work_key, description)."""
    data = ol_get(f'https://openlibrary.org{work_key}.json')
    if not data:
        return work_key, ''
    desc = data.get('description', '')
    if isinstance(desc, dict):
        desc = desc.get('value', '')
    if not isinstance(desc, str):
        desc = ''
    # Clean up markdown-style links and formatting
    desc = desc.replace('\r\n', '\n').strip()
    # Truncate very long descriptions
    if len(desc) > 2000:
        desc = desc[:1997] + '...'
    return work_key, desc


def fetch_books_for_subject(subject, needed, stdout):
    """Fetch popular books from Open Library subjects endpoint."""
    books = []
    seen_titles = set()
    offset = 0

    while len(books) < needed and offset < 5000:
        batch = min(250, needed - len(books) + 50)
        url = f'https://openlibrary.org/subjects/{subject}.json?limit={batch}&offset={offset}'
        data = ol_get(url)
        if not data:
            break

        works = data.get('works', [])
        if not works:
            break

        for w in works:
            title = (w.get('title') or '').strip()
            authors = w.get('authors') or []
            author = authors[0].get('name', 'Unknown') if authors else 'Unknown'
            year = w.get('first_publish_year')
            key = w.get('key', '')
            avail = w.get('availability') or {}
            identifier = avail.get('identifier', '')
            edition_key = avail.get('openlibrary_edition') or w.get('cover_edition_key', '')

            if not title or len(title) < 2:
                continue

            title_key = title.lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            # Build read URL
            read_url = ''
            if identifier:
                read_url = f'https://archive.org/details/{identifier}'
            elif edition_key:
                read_url = f'https://openlibrary.org/books/{edition_key}'
            elif key:
                read_url = f'https://openlibrary.org{key}'

            pub_date = None
            if year and 1000 <= year <= 2026:
                pub_date = date(year, 1, 1)

            # Generate a random ISBN (real ISBNs from search are unreliable)
            isbn = f'978{random.randint(1000000000, 9999999999)}'

            books.append({
                'title': title[:200],
                'author': author[:100],
                'isbn': isbn,
                'publication_date': pub_date,
                'read_url': read_url[:500],
                'work_key': key,
            })

            if len(books) >= needed:
                break

        offset += batch
        time.sleep(0.3)

    # Fetch descriptions in parallel
    if books:
        work_keys = [b['work_key'] for b in books if b['work_key']]
        stdout.write(f'  Fetching descriptions for {len(work_keys)} works...')
        desc_map = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(fetch_description, k): k for k in work_keys}
            for f in as_completed(futures):
                key, desc = f.result()
                if desc:
                    desc_map[key] = desc
        stdout.write(f'  Got {len(desc_map)} descriptions')
        for b in books:
            b['description'] = desc_map.get(b['work_key'], '')

    return books


class Command(BaseCommand):
    help = 'Fetch real books from Open Library and update existing Book records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--genre', type=str, default='',
            help='Only update a specific genre slug',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        only_genre = options['genre']
        genres = Genre.objects.all().order_by('name')
        total_updated = 0

        for genre in genres:
            slug = genre.slug
            if only_genre and slug != only_genre:
                continue

            subject = GENRE_SUBJECTS.get(slug, slug)
            books_qs = Book.objects.filter(genre=genre).order_by('id')
            needed = books_qs.count()

            if needed == 0:
                continue

            self.stdout.write(f'\n[{genre.name}] Fetching {needed} real books (subject: {subject})...')
            real_books = fetch_books_for_subject(subject, needed, self.stdout)
            self.stdout.write(f'  Got {len(real_books)} books total')

            if not real_books:
                self.stdout.write(self.style.WARNING(f'  Skipping - no results'))
                continue

            book_ids = list(books_qs.values_list('id', flat=True))
            updated = 0
            with_desc = 0

            for i, book_id in enumerate(book_ids):
                if i >= len(real_books):
                    break

                rb = real_books[i]
                if rb.get('description'):
                    with_desc += 1

                if dry_run:
                    desc_flag = ' [has desc]' if rb.get('description') else ''
                    read_flag = ' [readable]' if rb.get('read_url') else ''
                    self.stdout.write(f'  #{book_id}: {rb["title"]} — {rb["author"]}{desc_flag}{read_flag}')
                    updated += 1
                else:
                    try:
                        Book.objects.filter(id=book_id).update(
                            title=rb['title'],
                            author=rb['author'],
                            isbn=rb['isbn'],
                            description=rb.get('description', ''),
                            read_url=rb.get('read_url', ''),
                            publication_date=rb['publication_date'] or date(2000, 1, 1),
                        )
                        updated += 1
                    except IntegrityError:
                        try:
                            rb['isbn'] = f'978{random.randint(1000000000, 9999999999)}'
                            Book.objects.filter(id=book_id).update(
                                title=rb['title'],
                                author=rb['author'],
                                isbn=rb['isbn'],
                                description=rb.get('description', ''),
                                read_url=rb.get('read_url', ''),
                                publication_date=rb['publication_date'] or date(2000, 1, 1),
                            )
                            updated += 1
                        except Exception:
                            pass
                    except Exception as e:
                        self.stdout.write(f'    Skip #{book_id}: {e}')

            total_updated += updated
            self.stdout.write(self.style.SUCCESS(
                f'  Updated {updated}/{needed} books ({with_desc} with descriptions)'
            ))

            time.sleep(0.5)

        verb = 'Would update' if dry_run else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'\nDone! {verb} {total_updated} books total.'))

        if not dry_run:
            self.stdout.write('Run: python manage.py reindex_books  (to rebuild search index)')
