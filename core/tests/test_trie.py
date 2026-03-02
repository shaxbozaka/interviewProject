import threading

import pytest

from core.trie import Trie


class TestTrieBasic:
    def test_insert_and_search(self):
        trie = Trie()
        trie.insert('hello')
        assert trie.search('hello') is True
        assert trie.search('hell') is False
        assert trie.search('helloo') is False

    def test_empty_trie_search(self):
        trie = Trie()
        assert trie.search('anything') is False

    def test_insert_empty_string(self):
        trie = Trie()
        trie.insert('')
        assert len(trie) == 0

    def test_search_empty_string(self):
        trie = Trie()
        trie.insert('hello')
        assert trie.search('') is False

    def test_case_insensitive(self):
        trie = Trie()
        trie.insert('Hello World')
        assert trie.search('hello world') is True
        assert trie.search('HELLO WORLD') is True

    def test_preserves_original_casing(self):
        trie = Trie()
        trie.insert('Harry Potter', weight=10)
        results = trie.autocomplete('harry')
        assert results == ['Harry Potter']

    def test_duplicate_insert(self):
        trie = Trie()
        trie.insert('hello')
        trie.insert('hello')
        assert len(trie) == 1

    def test_len(self):
        trie = Trie()
        trie.insert('apple')
        trie.insert('app')
        trie.insert('application')
        assert len(trie) == 3


class TestTrieStartsWith:
    def test_prefix_exists(self):
        trie = Trie()
        trie.insert('hello')
        assert trie.starts_with('hel') is True

    def test_prefix_not_exists(self):
        trie = Trie()
        trie.insert('hello')
        assert trie.starts_with('xyz') is False

    def test_empty_prefix(self):
        trie = Trie()
        trie.insert('hello')
        assert trie.starts_with('') is False

    def test_full_word_as_prefix(self):
        trie = Trie()
        trie.insert('hello')
        assert trie.starts_with('hello') is True


class TestTrieAutocomplete:
    def test_basic_autocomplete(self):
        trie = Trie()
        trie.insert('apple')
        trie.insert('application')
        trie.insert('app')
        results = trie.autocomplete('app')
        assert 'apple' in results
        assert 'application' in results
        assert 'app' in results

    def test_autocomplete_with_limit(self):
        trie = Trie()
        for i in range(20):
            trie.insert(f'test{i:02d}')
        results = trie.autocomplete('test', limit=5)
        assert len(results) == 5

    def test_autocomplete_ordered_by_weight(self):
        trie = Trie()
        trie.insert('apple', weight=5)
        trie.insert('application', weight=10)
        trie.insert('app', weight=1)
        results = trie.autocomplete('app')
        assert results[0] == 'application'
        assert results[-1] == 'app'

    def test_autocomplete_no_matches(self):
        trie = Trie()
        trie.insert('hello')
        results = trie.autocomplete('xyz')
        assert results == []

    def test_autocomplete_empty_prefix(self):
        trie = Trie()
        trie.insert('hello')
        assert trie.autocomplete('') == []

    def test_autocomplete_same_weight_alphabetical(self):
        trie = Trie()
        trie.insert('banana', weight=5)
        trie.insert('band', weight=5)
        trie.insert('bat', weight=5)
        results = trie.autocomplete('ba')
        assert results == ['banana', 'band', 'bat']


class TestTrieDelete:
    def test_delete_existing(self):
        trie = Trie()
        trie.insert('hello')
        assert trie.delete('hello') is True
        assert trie.search('hello') is False
        assert len(trie) == 0

    def test_delete_nonexistent(self):
        trie = Trie()
        trie.insert('hello')
        assert trie.delete('world') is False
        assert len(trie) == 1

    def test_delete_preserves_siblings(self):
        trie = Trie()
        trie.insert('hello')
        trie.insert('help')
        trie.delete('hello')
        assert trie.search('hello') is False
        assert trie.search('help') is True

    def test_delete_preserves_parent_word(self):
        trie = Trie()
        trie.insert('app')
        trie.insert('apple')
        trie.delete('apple')
        assert trie.search('app') is True
        assert trie.search('apple') is False

    def test_delete_empty_string(self):
        trie = Trie()
        assert trie.delete('') is False


class TestTrieBulkInsert:
    def test_bulk_insert(self):
        trie = Trie()
        items = [('apple', 5), ('banana', 3), ('cherry', 7)]
        trie.bulk_insert(items)
        assert len(trie) == 3
        assert trie.search('apple') is True
        assert trie.search('banana') is True
        assert trie.search('cherry') is True

    def test_bulk_insert_skips_empty(self):
        trie = Trie()
        items = [('apple', 5), ('', 0), ('banana', 3)]
        trie.bulk_insert(items)
        assert len(trie) == 2


class TestTrieThreadSafety:
    def test_concurrent_inserts(self):
        trie = Trie()
        errors = []

        def insert_range(start, end):
            try:
                for i in range(start, end):
                    trie.insert(f'word{i}', weight=i)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=insert_range, args=(i * 100, (i + 1) * 100))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(trie) == 500

    def test_concurrent_read_write(self):
        trie = Trie()
        for i in range(100):
            trie.insert(f'word{i}', weight=i)
        errors = []

        def reader():
            try:
                for _ in range(50):
                    trie.autocomplete('word', limit=10)
            except Exception as e:
                errors.append(e)

        def writer():
            try:
                for i in range(100, 200):
                    trie.insert(f'word{i}', weight=i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(3)]
        threads.append(threading.Thread(target=writer))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors


class TestTrieSpecialCharacters:
    def test_spaces_in_words(self):
        trie = Trie()
        trie.insert('Harry Potter')
        assert trie.search('harry potter') is True
        results = trie.autocomplete('harry')
        assert results == ['Harry Potter']

    def test_numbers_in_words(self):
        trie = Trie()
        trie.insert('catch22')
        assert trie.search('catch22') is True

    def test_unicode_characters(self):
        trie = Trie()
        trie.insert('café')
        assert trie.search('café') is True
        results = trie.autocomplete('caf')
        assert results == ['café']
