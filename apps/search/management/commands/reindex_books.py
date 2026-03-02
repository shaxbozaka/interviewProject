from django.core.management.base import BaseCommand

from apps.search.es_client import ensure_index, reindex_all
from apps.search.trie_service import refresh_trie


class Command(BaseCommand):
    help = 'Reindex all books into Elasticsearch and rebuild the autocomplete trie'

    def handle(self, *args, **options):
        self.stdout.write('Creating/verifying ES index...')
        if ensure_index():
            self.stdout.write(self.style.SUCCESS('ES index ready'))
            self.stdout.write('Reindexing books...')
            reindex_all()
            self.stdout.write(self.style.SUCCESS('ES reindex complete'))
        else:
            self.stdout.write(self.style.WARNING('ES unavailable, skipping'))

        self.stdout.write('Rebuilding autocomplete trie...')
        refresh_trie()
        self.stdout.write(self.style.SUCCESS('Trie rebuilt'))
