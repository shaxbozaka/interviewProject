"""
Generator-based lazy exports for large datasets.

Uses Django's iterator() and yields rows one at a time to avoid
loading entire queryset into memory. Demonstrates Python generators
and lazy evaluation for code optimization.
"""
import csv
import io
from typing import Generator

from django.http import StreamingHttpResponse


def queryset_to_csv_generator(queryset, fields: list[str]) -> Generator[str, None, None]:
    """
    Lazily convert a queryset to CSV rows using a generator.

    Uses queryset.iterator() to avoid loading all objects into memory.
    Yields one CSV row at a time.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Header row
    writer.writerow(fields)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)

    # Data rows — iterator() uses server-side cursors for large datasets
    for obj in queryset.only(*fields).iterator(chunk_size=500):
        row = [getattr(obj, field, '') for field in fields]
        writer.writerow(row)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


def streaming_csv_response(queryset, fields: list[str], filename: str) -> StreamingHttpResponse:
    """Create a streaming HTTP response for CSV download."""
    generator = queryset_to_csv_generator(queryset, fields)
    response = StreamingHttpResponse(generator, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
