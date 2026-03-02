"""
Profiling and benchmarking script.

Usage:
    python scripts/benchmark.py profile_queries
    python scripts/benchmark.py profile_cache
    python scripts/benchmark.py profile_trie
    python scripts/benchmark.py memory_report

Requires Django to be set up (DJANGO_SETTINGS_MODULE).
"""
import cProfile
import os
import pstats
import sys
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()


def profile_queries():
    """Profile database query performance with EXPLAIN ANALYZE."""
    from django.db import connection
    from apps.books.models import Book

    print('=== Query Profiling ===\n')

    # 1. Simple list query
    start = time.perf_counter()
    list(Book.objects.all()[:100])
    elapsed = time.perf_counter() - start
    print(f'Book.objects.all()[:100]: {elapsed*1000:.2f}ms')
    print(f'  Queries: {len(connection.queries)}\n')

    connection.queries.clear()

    # 2. Annotated query (with ratings)
    from django.db.models import Avg
    start = time.perf_counter()
    list(Book.objects.annotate(avg_rating=Avg('ratings__rate'))[:100])
    elapsed = time.perf_counter() - start
    print(f'Book with ratings annotation: {elapsed*1000:.2f}ms')
    print(f'  Queries: {len(connection.queries)}\n')

    # 3. EXPLAIN ANALYZE on key queries
    with connection.cursor() as cursor:
        cursor.execute(
            "EXPLAIN ANALYZE SELECT * FROM books_book WHERE title ILIKE %s",
            ['%python%']
        )
        plan = cursor.fetchall()
        print('EXPLAIN ANALYZE (title ILIKE):\n')
        for row in plan:
            print(f'  {row[0]}')


def profile_cache():
    """Benchmark the two-tier caching system."""
    from core.caching import cache_get, cache_set, cache_invalidate_pattern

    print('=== Cache Profiling ===\n')

    # Write benchmark
    iterations = 1000
    start = time.perf_counter()
    for i in range(iterations):
        cache_set(f'bench:key:{i}', f'value_{i}', l1_ttl=60.0, l2_ttl=300)
    write_time = time.perf_counter() - start
    print(f'Cache write ({iterations} ops): {write_time*1000:.2f}ms ({write_time/iterations*1000:.3f}ms/op)')

    # Read benchmark (L1 hits)
    start = time.perf_counter()
    for i in range(iterations):
        cache_get(f'bench:key:{i}')
    l1_time = time.perf_counter() - start
    print(f'Cache read L1 ({iterations} ops): {l1_time*1000:.2f}ms ({l1_time/iterations*1000:.3f}ms/op)')

    # Invalidate and read (L2 hits)
    cache_invalidate_pattern('bench')
    start = time.perf_counter()
    for i in range(iterations):
        cache_get(f'bench:key:{i}')
    l2_time = time.perf_counter() - start
    print(f'Cache read L2 ({iterations} ops): {l2_time*1000:.2f}ms ({l2_time/iterations*1000:.3f}ms/op)')


def profile_trie():
    """Benchmark the Trie data structure."""
    from core.trie import Trie

    print('=== Trie Profiling ===\n')

    trie = Trie()

    # Generate test data
    words = [f'word_{i:06d}' for i in range(10000)]

    # Insert benchmark
    start = time.perf_counter()
    trie.bulk_insert([(w, i) for i, w in enumerate(words)])
    insert_time = time.perf_counter() - start
    print(f'Bulk insert (10,000 words): {insert_time*1000:.2f}ms')

    # Search benchmark
    start = time.perf_counter()
    for w in words[:1000]:
        trie.search(w)
    search_time = time.perf_counter() - start
    print(f'Search (1,000 lookups): {search_time*1000:.2f}ms ({search_time/1000*1000:.3f}ms/op)')

    # Autocomplete benchmark
    start = time.perf_counter()
    for _ in range(1000):
        trie.autocomplete('word_00', limit=10)
    auto_time = time.perf_counter() - start
    print(f'Autocomplete (1,000 prefix searches): {auto_time*1000:.2f}ms ({auto_time/1000*1000:.3f}ms/op)')

    print(f'\nTrie size: {len(trie)} entries')


def memory_report():
    """Memory usage report using memory_profiler."""
    try:
        from memory_profiler import memory_usage
    except ImportError:
        print('Install memory-profiler: pip install memory-profiler')
        return

    print('=== Memory Report ===\n')

    def create_trie():
        from core.trie import Trie
        trie = Trie()
        trie.bulk_insert([(f'word_{i:06d}', i) for i in range(50000)])
        return trie

    def create_lru():
        from core.cache import LRUCache
        cache = LRUCache(capacity=10000, default_ttl=300.0)
        for i in range(10000):
            cache.put(f'key_{i}', f'value_{i}')
        return cache

    baseline = memory_usage(max_usage=True)

    trie_mem = memory_usage((create_trie,), max_usage=True)
    print(f'Trie (50k words): {trie_mem - baseline:.1f} MiB')

    lru_mem = memory_usage((create_lru,), max_usage=True)
    print(f'LRU Cache (10k entries): {lru_mem - baseline:.1f} MiB')


def cprofile_report():
    """Generate cProfile report for key operations."""
    print('=== cProfile Report ===\n')

    profiler = cProfile.Profile()
    profiler.enable()

    # Profile trie operations
    from core.trie import Trie
    trie = Trie()
    for i in range(5000):
        trie.insert(f'word_{i:05d}', weight=i)
    for _ in range(1000):
        trie.autocomplete('word_0', limit=10)

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)


COMMANDS = {
    'profile_queries': profile_queries,
    'profile_cache': profile_cache,
    'profile_trie': profile_trie,
    'memory_report': memory_report,
    'cprofile_report': cprofile_report,
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f'Usage: python scripts/benchmark.py <command>')
        print(f'Commands: {", ".join(COMMANDS.keys())}')
        sys.exit(1)

    COMMANDS[sys.argv[1]]()
