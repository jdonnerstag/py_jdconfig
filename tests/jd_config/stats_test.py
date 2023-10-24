#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
import os
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from jd_config import ConfigStats, JDConfig, Placeholder

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args) -> Path:
    return Path(os.path.join(os.path.dirname(__file__), "data", *args))


def test_simple_stats(monkeypatch):
    monkeypatch.setenv("DB_USER", "dbuser")

    data = """
        a1: aa
        a2:
            b1: 'b'
            b2:
            - 1
            - 2
            - c1: 'c'
            b3: '{ref:a1}'
            b4: '{ref:a1, {ref:a3}} - {ref:a2.b1}'
        a3: '{env:DB_USER}'
    """

    cfg = JDConfig(ini_file=None)
    cfg.load(StringIO(data))
    stats = ConfigStats().create(cfg)
    assert stats
    assert stats.dict_count == 3
    assert stats.list_count == 1
    assert stats.value_count == 8
    assert stats.max_depth == 4
    assert stats.env_name is None
    assert stats.ini_env_var is None
    assert stats.ini_file is None
    assert stats.envvars == {"DB_USER"}
    assert len(stats.files) == 1
    assert stats.placeholders == {"ref": 4, "env": 1}


def test_load_jdconfig_1(monkeypatch):
    # config-1 contains a simple config file, with no imports.

    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    cfg = JDConfig(ini_file=None)
    cfg.ini.config_dir = data_dir("configs-1")
    cfg.ini.config_file = "config.yaml"
    cfg.ini.default_env = "dev"
    data = cfg.load()
    assert data

    stats = ConfigStats().create(cfg)
    assert stats
    assert stats.dict_count == 2
    assert stats.list_count == 0
    assert stats.value_count == 9
    assert stats.max_depth == 2
    assert stats.env_name is None
    assert stats.ini_env_var is None
    assert stats.ini_file is None
    assert stats.envvars == {"DB_USER", "DB_PASS", "DB_NAME"}
    assert len(stats.files) == 1
    assert stats.placeholders == {"ref": 4, "env": 3}


def test_load_jdconfig_2(monkeypatch):
    # config-2 is using some import placeholders, including dynamic ones,
    # where the actually path refers to config value.

    cfg = JDConfig(ini_file=None)
    cfg.ini.env = None  # Make sure, we are not even trying to load an env file
    # config-2 has imports. Make sure, it is available for imports.
    cfg.ini.config_dir = data_dir("configs-2")
    # if config_dir provided to load() it is only used for this one file
    data = cfg.load("main_config.yaml")
    assert data

    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    stats = ConfigStats().create(cfg)
    assert stats
    assert stats.dict_count == 12
    assert stats.list_count == 1
    assert stats.value_count == 33
    assert stats.max_depth == 4
    assert stats.env_name is None
    assert stats.ini_env_var is None
    assert stats.ini_file is None
    assert stats.envvars == {"DB_USER", "DB_PASS", "DB_NAME"}
    assert len(stats.files) == 4
    assert stats.placeholders == {
        "ref": 7,
        "env": 3,
        "timestamp": 1,
        "import": 3,
        "global": 3,
    }


def test_load_jdconfig_2_with_env(monkeypatch):
    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    cfg = JDConfig(ini_file=None)
    cfg.ini.env = "jd_dev"  # Apply own env specific changes
    cfg.ini.config_dir = data_dir("configs-2")
    data = cfg.load("main_config.yaml")
    assert data

    stats = ConfigStats().create(cfg)
    assert stats
    assert stats.dict_count == 11
    assert stats.list_count == 1
    assert stats.value_count == 27
    assert stats.max_depth == 4
    assert stats.env_name == "jd_dev"
    assert stats.ini_env_var is None
    assert stats.ini_file is None
    assert stats.envvars == set()
    assert len(stats.files) == 6
    assert stats.placeholders == {"ref": 3, "timestamp": 1, "import": 3, "global": 2}


def test_load_jdconfig_4(monkeypatch):
    # config-4 is is about simple {import:}, {ref:} and {global:}

    cfg = JDConfig(ini_file=None)
    cfg.ini.env = None  # Make sure, we are not even trying to load an env file
    cfg.ini.config_dir = data_dir("configs-4")  # configure the directory for imports
    data = cfg.load("config.yaml")
    assert data
    assert data.get("c.a") == "2aa"
    assert data.get("d") == "2aa"

    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    stats = ConfigStats().create(cfg)
    assert stats
    assert stats.dict_count == 2
    assert stats.list_count == 0
    assert stats.value_count == 11
    assert stats.max_depth == 2
    assert stats.env_name is None
    assert stats.ini_env_var is None
    assert stats.ini_file is None
    assert stats.envvars == set()
    assert len(stats.files) == 2
    assert stats.placeholders == {"ref": 7, "import": 1, "global": 2}


@dataclass
class MyBespokePlaceholder(Placeholder):
    """This is also a test for a placeholder that does not take any parameters"""

    def resolve(self, *_, **__) -> str:
        return "value"


def test_add_placeholder():
    cfg = JDConfig(ini_file=None)
    cfg.placeholder_registry["bespoke"] = MyBespokePlaceholder

    DATA = """
        a: aa
        b: bb
        c: '{bespoke:}'
    """

    file_like_io = StringIO(DATA)
    data = cfg.load(file_like_io)
    assert data

    stats = ConfigStats().create(cfg)
    assert stats
    assert stats.dict_count == 1
    assert stats.list_count == 0
    assert stats.value_count == 3
    assert stats.max_depth == 1
    assert stats.env_name is None
    assert stats.ini_env_var is None
    assert stats.ini_file is None
    assert stats.envvars == set()
    assert len(stats.files) == 1
    assert stats.placeholders == {"bespoke": 1}
