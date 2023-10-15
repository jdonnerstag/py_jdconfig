#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
import os
import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pytest

from jd_config import ConfigException, JDConfig, NodeEvent, Placeholder

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args) -> Path:
    return Path(os.path.join(os.path.dirname(__file__), "data", *args))


def test_load_jdconfig_1():
    # config-1 contains a simple config file, with no imports.

    cfg = JDConfig(ini_file=None)
    cfg.config_dir = data_dir("configs-1")
    cfg.config_file = "config.yaml"
    cfg.default_env = "dev"

    data = cfg.load()
    assert data

    # Provide the config file name. Note, that it'll not change or set the
    # config_dir. Any config files imported, are imported relativ to the
    # config_dir configured (or preset) in config.ini
    cfg = JDConfig(ini_file=None)
    file = data_dir("configs-1", "config.yaml")
    data = cfg.load(file)
    assert data

    # Provide a filename and a config_dir. All config imports, will be executed
    # relativ to the config_dir provided.
    # The config file might still be relativ or absolut.
    cfg = JDConfig(ini_file=None)
    config_dir = data_dir("configs-1")
    data = cfg.load("config.yaml", config_dir)
    assert data

    file = data_dir("configs-1", "config.yaml")
    data = cfg.load(file.absolute(), config_dir)
    assert data


def test_jdconfig_1_placeholders(monkeypatch):
    cfg = JDConfig(ini_file=None)
    config_dir = data_dir("configs-1")
    data = cfg.load("config.yaml", config_dir)
    assert data

    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    assert cfg.get("DB_USER") == "dbuser"
    assert cfg.get("DB_PASS") == "dbpass"
    assert cfg.get("DB_NAME") == "dbname"

    assert cfg.get("connection_string") == "dbuser/dbpass@dbname"
    assert cfg.get("db_job_name") == "IMPORT_FILES"
    assert cfg.get("batch_size") == 1000

    assert cfg.get("schematas.engine") == "dbuser"
    assert cfg.get("schematas.maintenance") == "xxx"
    assert cfg.get("schematas.e2e") == "xxx"


def test_load_jdconfig_4():
    # config-4 is is about simple {import:}, {ref:} and {global:}

    cfg = JDConfig(ini_file=None)
    cfg.env = None  # Make sure, we are not even trying to load an env file
    cfg.config_dir = data_dir("configs-4")  # configure the directory for imports
    data = cfg.load("config.yaml")
    assert data

    assert cfg.get("a") == "aa"
    assert cfg.get("b") == "aa"
    assert cfg.get("c")

    assert cfg.get("c.a") == "2aa"
    assert cfg.get("c.b") == "2aa"
    assert cfg.get("c.c") == "aa"
    assert cfg.get("c.d") == "2aa"
    assert cfg.get("c.e") == "aa"
    assert cfg.get("c.f") == "aa"

    assert cfg.get("d") == "2aa"
    assert cfg.get("e") == "2aa"
    assert cfg.get("f") == "aa"


def test_load_jdconfig_2(monkeypatch):
    # config-2 is using some import placeholders, including dynamic ones,
    # where the actually path refers to config value.

    cfg = JDConfig(ini_file=None)
    cfg.env = None  # Make sure, we are not even trying to load an env file
    cfg.config_dir = data_dir(
        "configs-2"
    )  # config-2 has imports. Make sure, it is available for imports.
    data = cfg.load(
        "main_config.yaml"
    )  # if config_dir provided to load() it is only used for this one file
    assert data

    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    assert re.match(r"\d{8}-\d{6}", cfg.get("timestamp"))
    assert cfg.get("db") == "oracle"
    # TODO we should cache the imported files
    # TODO need to resolve DB_USER against the file it is in.
    assert cfg.get("database.DB_USER") == "dbuser"
    assert cfg.get("database.DB_PASS") == "dbpass"
    assert cfg.get("database.DB_NAME") == "dbname"
    assert cfg.get("database.connection_string") == "oracle:dbuser/dbpass@dbname"

    assert cfg.get("debug.log_progress_after") == 20_000


@dataclass
class MyBespokePlaceholder(Placeholder):
    """This is also a test for a placeholder that does not take any parameters"""

    def resolve(self, *_, **__) -> str:
        return "value"


def test_add_placeholder():
    cfg = JDConfig(ini_file=None)
    cfg.register_placeholder_handler("bespoke", MyBespokePlaceholder)

    DATA = """
        a: aa
        b: bb
        c: '{bespoke:}'
    """

    file_like_io = StringIO(DATA)
    data = cfg.load(file_like_io)
    assert data

    assert len(cfg.files_loaded) == 1
    assert cfg.files_loaded[0] == "<data>"

    assert cfg.get("c") == "value"


def test_load_jdconfig_3():
    # config-3 has a file recursion

    cfg = JDConfig(ini_file=None)
    config_dir = data_dir("configs-3")

    with pytest.raises(ConfigException):
        cfg.load("config.yaml", config_dir)

    assert len(cfg.file_recursions) > 0


def test_walk():
    cfg = JDConfig(ini_file=None)

    DATA = """
        a: aa
        b:
            b1:
                c1: "1cc"
                c2: "2cc"
            b2: 22
    """

    file_like_io = StringIO(DATA)
    data = cfg.load(file_like_io)
    assert data

    data = list(cfg.walk(resolve=True))
    assert len(data) == 4
    data.remove(NodeEvent(("a",), "aa"))
    data.remove(NodeEvent(("b", "b1", "c1"), "1cc"))
    data.remove(NodeEvent(("b", "b1", "c2"), "2cc"))
    data.remove(NodeEvent(("b", "b2"), 22))

    data = list(cfg.walk(resolve=False))
    assert len(data) == 4
    data.remove(NodeEvent(("a",), "aa"))
    data.remove(NodeEvent(("b", "b1", "c1"), "1cc"))
    data.remove(NodeEvent(("b", "b1", "c2"), "2cc"))
    data.remove(NodeEvent(("b", "b2"), 22))


def test_load_jdconfig_2_with_env(monkeypatch):
    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    cfg = JDConfig(ini_file=None)
    cfg.env = "jd_dev"  # Apply own env specific changes

    config_dir = data_dir("configs-2")
    data = cfg.load("main_config.yaml", config_dir)
    assert data
    assert len(cfg.files_loaded) == 5
    assert cfg.files_loaded[0].parts[-2:] == ("configs-2", "main_config.yaml")
    assert cfg.files_loaded[1].parts[-2:] == ("configs-2", "main_config-jd_dev.yaml")
    assert len(cfg.file_recursions) == 0

    assert re.match(r"\d{8}-\d{6}", cfg.get("timestamp"))
    assert cfg.get("db") == "mysql"
    assert cfg.get("database.driver") == "mysql"
    assert cfg.get("database.user") == "omry"
    assert cfg.get("database.password") == "secret"
    assert cfg.get("database.DB_USER", None) is None
    assert cfg.get("database.DB_PASS", None) is None
    assert cfg.get("database.DB_NAME", None) is None
    assert cfg.get("database.connection_string", None) is None

    assert cfg.get("debug.log_progress_after") == 20_000
