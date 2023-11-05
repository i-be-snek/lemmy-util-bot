import os
from collections import OrderedDict
from unittest import mock

import pytest
from filestack import Client, Filelink
from filestack.exceptions import FilestackHTTPError
from tinydb import Query, TinyDB

from src.helper import (
    Config,
    DataBase,
    FileDownloadError,
    FileUploadError,
    Thread,
    Util,
)
from tests import items


class TestClassHelper:
    def test_check_configs_missing_config(self):
        with pytest.raises(AssertionError):
            Config(items.config_missing_keys)

    def test_check_configs(self):
        Config(items.full_config)

    def test_check_configs_ignore_list(self):
        assert Config(items.full_config).THREADS_TO_IGNORE == [
            Thread.mirrored,
            Thread.pinned,
            Thread.nsfw,
        ]

    def test_check_prod_configs(self):
        from dotenv import dotenv_values

        assert Config(dotenv_values(".env"))


@pytest.mark.parametrize("test_filestack", [DataBase("tests/filestack_tests.txt")])
class TestClassDataBase:
    def test__upload_backup_bad_apikey_app_key_fail(self, test_filestack):
        c = Config(items.full_config)

        with pytest.raises(FilestackHTTPError):
            test_filestack._upload_backup(
                c.FILESTACK_APP_SECRET, c.FILESTACK_API_KEY, "test.json"
            )

    def test__upload_backup_fail(self, test_filestack):
        c = Config(items.full_config)
        with mock.patch.object(Client, "upload", return_value=None):
            with pytest.raises(FileUploadError):
                file = test_filestack._upload_backup(
                    c.FILESTACK_APP_SECRET, c.FILESTACK_API_KEY, "test.json"
                )

    def test_get_backup_bad_apikey_app_key_fail(self, test_filestack):
        c = Config(items.full_config)

        with pytest.raises(FilestackHTTPError):
            test_filestack.get_backup(
                c.FILESTACK_APP_SECRET, c.FILESTACK_API_KEY, c.FILESTACK_HANDLE_REFRESH
            )

    def test_get_backup_fail(self, test_filestack):
        c = Config(items.full_config)
        with mock.patch.object(Filelink, "download", return_value=None):
            with pytest.raises(FileDownloadError):
                file = test_filestack.get_backup(
                    c.FILESTACK_APP_SECRET,
                    c.FILESTACK_API_KEY,
                    c.FILESTACK_HANDLE_REFRESH,
                )

    def test_refresh_backup_bad_apikey_app_key_fail(self, test_filestack):
        c = Config(items.full_config)

        with pytest.raises(FilestackHTTPError):
            test_filestack.refresh_backup(
                c.FILESTACK_APP_SECRET, c.FILESTACK_API_KEY, c.FILESTACK_HANDLE_REFRESH
            )

    def test_refresh_backup_fail(self, test_filestack):
        c = Config(items.full_config)
        with mock.patch.object(Filelink, "overwrite", return_value=None):
            with pytest.raises(FileUploadError):
                file = test_filestack.refresh_backup(
                    c.FILESTACK_APP_SECRET,
                    c.FILESTACK_API_KEY,
                    c.FILESTACK_HANDLE_REFRESH,
                )


class TestClassUtil:
    def test__getattr_mod_success(self):
        assert Util._getattr_mod(os, "__name__") == "os"

    def test__getattr_mod_fail(self):
        assert Util._getattr_mod(os, "non_existent_attribute") == None

    def test__check_thread_in_db(self):
        test_db = TinyDB(items.test_db_path)
        assert Util._check_thread_in_db(reddit_id="test_1234", DB=test_db) == False

    def test__check_thread_in_db(self):
        test_db = TinyDB(items.test_db_path)
        assert Util._check_thread_in_db(reddit_id="test_170jhq3", DB=test_db) == True

    def test__check_if_image_success(self):
        assert Util._check_if_image(items.cat_image) == items.cat_image

    def test__check_if_image_non_image(self):
        assert Util._check_if_image(items.not_image) is None

    def test__check_if_image_bad_input(self):
        assert Util._check_if_image(123) is None
