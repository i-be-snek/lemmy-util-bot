from collections import OrderedDict
from unittest import mock

import pytest
from filestack import Client, Filelink
from filestack.exceptions import FilestackHTTPError

from src.helper import Config, DataBase, FileDownloadError, FileUploadError
from tests import items


class TestClassHelper:
    def test_check_configs_missing_config(self):
        with pytest.raises(AssertionError):
            Config(items.config_missing_keys)

    def test_check_configs(self):
        Config(items.full_config)


@pytest.mark.parametrize("test_filestack", [DataBase("tests/filestack_tests.txt")])
class TestClassDataBase:
    def test__upload_backup_bad_token_app_key_fail(self, test_filestack):
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

    def test_get_backup_bad_token_app_key_fail(self, test_filestack):
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

    def test_refresh_backup_bad_token_app_key_fail(self, test_filestack):
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
