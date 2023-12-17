from unittest import mock

from src.auto_mod import AutoMod, LemmyThread
from tests import items


class TestClassAutoMod:
    def test__find_new_threads(self):
        mock_lemmy = mock.MagicMock()
        mock_lemmy.post.list.return_value = [
            items.thread_list_response_lemmy_unsaved,
            # saved posts already contain a mod comment
            items.thread_list_response_lemmy_saved,
        ]

        auto_mod = AutoMod(mock_lemmy, "world", "TestModBot")

        assert auto_mod._find_new_threads() == [LemmyThread(False, False, False, 3, False, False, False)]

    def test__comment_as_mod(self):
        mock_lemmy = mock.MagicMock()
        mock_lemmy.comment.create.return_value = {"comment_view": {"comment": {"id": 1}}}
        mock_lemmy.comment.distinguish.return_value = True
        auto_mod = AutoMod(mock_lemmy, "world", "TestModBot")
        assert auto_mod._comment_as_mod(content="Test Content", post_id=123) == 1
