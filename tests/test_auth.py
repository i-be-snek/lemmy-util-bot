from unittest import mock

import praw
import pytest

from src.auth import lemmy_auth, lemmy_init_instance, lemmy_login, reddit_oauth
from src.helper import Config
from tests import items


@pytest.mark.parametrize("incorrect_configs", [Config(items.full_config)])
class TestClassAuthBadConfig:
    def test_reddit_oauth_fail(self, incorrect_configs):
        assert reddit_oauth(incorrect_configs) == None

    def test_reddit_oauth_success(self, incorrect_configs):
        mock_reddit = mock.Mock()
        mock_reddit.user.me().return_value = "BurntSublime31"
        with mock.patch.object(praw, "Reddit", return_value=mock_reddit):
            assert reddit_oauth(incorrect_configs)

    def test_lemmy_auth_fail(self, incorrect_configs):
        assert lemmy_auth(incorrect_configs) == None

    def test_lemmy_auth_success(self, incorrect_configs):
        assert lemmy_auth(incorrect_configs) == None

    def test_lemmy_init_instance_fail(self, incorrect_configs):
        assert lemmy_init_instance(incorrect_configs.LEMMY_INSTANCE) == None

    def test_lemmy_login_fail(self, incorrect_configs):
        mock_lemmy = mock.Mock()
        mock_lemmy.log_in = mock.MagicMock(side_effect=Exception("Test"))

        assert (
            lemmy_login(
                mock_lemmy,
                incorrect_configs.LEMMY_USERNAME,
                incorrect_configs.LEMMY_PASSWORD,
            )
            == None
        )


class TestClassAuth:
    def test_lemmy_init_instance_success(self):
        assert lemmy_init_instance("https://lemmy.world")
