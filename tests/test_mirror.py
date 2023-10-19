import os
from unittest import mock

import praw
import pytest
from tinydb import Query, TinyDB

from src.helper import Config
from src.mirror import (
    _check_thread_in_db,
    _extract_threads_to_mirror,
    _getattr_mod,
    _insert_thread_into_db,
    get_threads_from_reddit,
    mirror_threads_to_lemmy,
)
from tests import items


class TestClassMirror:
    def test__check_thread_in_db(self):
        test_db = TinyDB(items.test_db_path)
        assert _check_thread_in_db(reddit_id="test_1234", DB=test_db) == False

    def test__check_thread_in_db(self):
        test_db = TinyDB(items.test_db_path)
        assert _check_thread_in_db(reddit_id="test_170jhq3", DB=test_db) == True

    def test__extract_threads_to_mirror_no_listing(self):
        test_db = TinyDB(items.test_db_path)
        assert _extract_threads_to_mirror([], test_db) == list(dict())
        test_db.close()

    def test_get_threads_from_reddit(self):
        # reddit = None
        # threads = get_threads_from_reddit(reddit, "test_sub", test_db)
        # assert threads == []
        pass

    def test_mirror_threads_to_lemmy_no_threads(self):
        test_db = TinyDB(items.test_db_path)
        mock_lemmy = mock.Mock()
        mirror = mirror_threads_to_lemmy(
            lemmy=mock_lemmy,
            threads_to_mirror=[],
            community="fake_community",
            DB=test_db,
            delay=0
        )
        assert mirror == 0
        test_db.close()

    def test_mirror_threads_to_lemmy_already_mirrored_threads(self):
        test_db = TinyDB(items.test_db_path)
        mock_lemmy = mock.Mock()
        threads_to_mirror = test_db.all()
        mirror = mirror_threads_to_lemmy(
            lemmy=mock_lemmy,
            threads_to_mirror=threads_to_mirror,
            community="fake_community",
            DB=test_db,
            delay=0
        )
        assert mirror == 0
        test_db.close()

    def test_mirror_threads_to_lemmy_no_url(self):
        test_db = TinyDB(items.test_db_path)
        mock_lemmy = mock.Mock()
        threads_to_mirror = [items.thread_no_url, items.thread]
        mirror = mirror_threads_to_lemmy(
            lemmy=mock_lemmy,
            threads_to_mirror=threads_to_mirror,
            community="fake_community",
            DB=test_db,
            delay=0
        )
        
        q = Query()
        test_db.remove(q.reddit_id == items.thread_no_url['reddit_id'])
        test_db.remove(q.reddit_id == items.thread['reddit_id'])

        test_db.close()
        assert mirror == 1


    def test__getattr_mod_success(self):
        assert _getattr_mod(os, "__name__") == "os"

    def test__getattr_mod_fail(self):
        assert _getattr_mod(os, "non_existent_attribute") == None
