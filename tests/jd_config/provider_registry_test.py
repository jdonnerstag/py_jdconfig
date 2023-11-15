#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from io import StringIO
import os
import logging
from pathlib import Path
from typing import Any, Mapping, Optional

import pytest

from jd_config import (
    JDConfig,
    DEFAULT,
    ConfigException,
    DeepGetter,
    EnvPlaceholder,
    GetterContext,
    GlobalRefPlaceholder,
    ImportPlaceholder,
    Placeholder,
    RefPlaceholder,
    Resolver,
)
from jd_config.provider_registry import ProviderPlugin

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class DemoProviderPlugin(ProviderPlugin):
    """The default yaml file and bytes loader"""

    name: str = "Demo Provider"

    def load(self, name: Optional[Path | StringIO], **kvargs) -> Mapping | None:
        """Load and return the data, or return None to indicate that the
        provider does not know how to handle this URL/file
        """
        if name != "config-2.yaml":
            return None

        data = {
            "a": 1,
            "b": 2,
            "c": 3,
            "d": 4,
            "e": 5,
            "f": 6,
        }

        return data


def data_dir(*args) -> Path:
    return Path(os.path.join(os.path.dirname(__file__), "data", *args))


def test_load_jdconfig_4():
    # config-4 is about simple {import:}, {ref:} and {global:}

    cfg = JDConfig(ini_file=None)
    cfg.ini.env = None  # Make sure, we are not even trying to load an env file
    cfg.ini.config_dir = data_dir("configs-4")  # configure the directory for imports
    data = cfg.load("config.yaml")
    assert data

    assert cfg.get("c.a") == "2aa"
    assert cfg.get("c.c") == "aa"
    assert cfg.get("d") == "2aa"
    assert cfg.get("e") == "2aa"
    assert cfg.get("f") == "aa"

    # Add the provider
    cfg.provider_registry.insert(0, DemoProviderPlugin(cfg))
    data = cfg.load("config.yaml")
    assert data

    assert cfg.get("c.a") == 1
    assert cfg.get("c.c") == 3
    assert cfg.get("d") == 1
    assert cfg.get("e") == 2
    assert cfg.get("f") == 3
