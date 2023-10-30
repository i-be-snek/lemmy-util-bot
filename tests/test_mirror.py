import os
from unittest import mock

import praw
import pytest
from tinydb import Query, TinyDB

from src.helper import Config, Thread, Util
from src.mirror import (
    _extract_threads_to_mirror,
    get_threads_from_reddit,
    mirror_threads_to_lemmy,
)
from tests import items


class TestClassMirror:
    def test__extract_threads_to_mirror_no_listing(self):
        test_db = TinyDB(items.test_db_path)
        assert _extract_threads_to_mirror([], test_db) == list(dict())
        test_db.close()

    def test__extract_threads_to_mirror_ignore_poll_no_valid_threads(self):
        test_db = TinyDB(items.test_db_path)
        mock_listing = mock.MagicMock()
        mock_listing.name = "tg_2ggk3"
        mock_listing.stickied = None
        mock_listing.over_18 = False
        mock_listing.poll_data = True  # is a poll thread
        mock_listing.is_locked = False
        mock_listing.is_video = False
        mock_listing.url = "https://example.com"
        mock_listing.title = "Test title"
        mock_listing.selftext = "Test body"
        mock_listing.permalink = "comments/tg_2ggk3"
        mock_listing.link_flair_text = None

        threads_to_mirror = _extract_threads_to_mirror(
            [mock_listing], test_db, [Thread.poll]
        )
        assert len(threads_to_mirror) == 0

    def test__extract_threads_to_mirror_ignore_poll_two_valid_threads(self):
        test_db = TinyDB(items.test_db_path)
        mock_listing = mock.MagicMock()
        mock_listing.name = "tg_2ggk3"
        mock_listing.stickied = None
        mock_listing.over_18 = False
        mock_listing.poll_data = False  # is not a poll thread
        mock_listing.is_locked = False
        mock_listing.is_video = False
        mock_listing.url = "https://example.com"
        mock_listing.title = "Test title"
        mock_listing.selftext = "Test body"
        mock_listing.permalink = "comments/tg_2ggk3"
        mock_listing.link_flair_text = None

        threads_to_mirror = _extract_threads_to_mirror(
            [mock_listing, mock_listing], test_db, [Thread.poll]
        )
        assert len(threads_to_mirror) == 2

    def test_mirror_threads_to_lemmy_no_threads(self):
        test_db = TinyDB(items.test_db_path)
        mock_lemmy = mock.Mock()
        mirror = mirror_threads_to_lemmy(
            lemmy=mock_lemmy,
            threads_to_mirror=[],
            community="fake_community",
            DB=test_db,
            delay=0,
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
            delay=0,
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
            delay=0,
        )

        q = Query()
        test_db.remove(q.reddit_id == items.thread_no_url["reddit_id"])
        test_db.remove(q.reddit_id == items.thread["reddit_id"])

        test_db.close()
        assert mirror == 1
