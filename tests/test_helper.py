from collections import OrderedDict

import pytest

from src.helper import Config
from tests.items import config, config_missing_keys


class TestClassHelper:
    def test_check_configs_missing_config(self):
        with pytest.raises(AssertionError):
            Config(config_missing_keys)

    def test_check_configs(self):
        Config(config)
