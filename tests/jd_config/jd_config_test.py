#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from dataclasses import dataclass
from io import StringIO
import os
import re
import logging
import pytest
from jd_config import JDConfig, Placeholder, ConfigException, YamlObj, NodeEvent

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args):
    return os.path.join(os.path.dirname(__file__), "data", *args)

def test_load_jdconfig_1():
    # config-1 contains a simple config file, with no imports.

    # Use the config.ini configs to load the config files
    cfg = JDConfig(ini_file = None)
    cfg.config_dir = data_dir("configs-1")
    cfg.config_file = "config.yaml"
    cfg.default_env = "dev"

    data = cfg.load()
    assert data
    assert len(cfg.files_loaded) == 1
    assert cfg.files_loaded[0].parts[-2:] == ("configs-1", "config.yaml")
    assert len(cfg.file_recursions) == 0

    # Provide the config file name. Note, that it'll not change or set the
    # config_dir. Any config files imported, are imported relativ to the
    # config_dir configured (or preset) in config.ini
    cfg = JDConfig(ini_file = None)
    file = data_dir("configs-1", "config.yaml")
    data = cfg.load(file)
    assert data

    # Provide a filename and a config_dir. All config imports, will be executed
    # relativ to the config_dir provided.
    # The config file might still be relativ or absolut.
    cfg = JDConfig(ini_file = None)
    config_dir = data_dir("configs-1")
    data = cfg.load("config.yaml", config_dir)
    assert data

    file = os.path.abspath(data_dir("configs-1", "config.yaml"))
    data = cfg.load(file, config_dir)
    assert data

def test_jdconfig_1_placeholders(monkeypatch):
    cfg = JDConfig(ini_file = None)
    config_dir = data_dir("configs-1")
    data = cfg.load("config.yaml", config_dir)
    assert data

    monkeypatch.setenv('DB_USER', 'dbuser')
    monkeypatch.setenv('DB_PASS', 'dbpass')
    monkeypatch.setenv('DB_NAME', 'dbname')

    assert cfg.get("DB_USER") == "dbuser"
    assert cfg.get("DB_PASS") == "dbpass"
    assert cfg.get("DB_NAME") == "dbname"

    assert cfg.get("connection_string") == "dbuser/dbpass@dbname"
    assert cfg.get("db_job_name") == "IMPORT_FILES"
    assert cfg.get("batch_size") ==  1000

    assert cfg.get("schematas.engine") == "dbuser"
    assert cfg.get("schematas.maintenance") == "xxx"
    assert cfg.get("schematas.e2e") == "xxx"


def test_post_load():
    # TODO Test post_load()
    pass


def test_load_jdconfig_2(monkeypatch):
    # config-2 is using some import placeholders, including dynamic ones,
    # where the actually path refers to config value.

    # Apply config_dir to set working directory for relativ yaml imports
    cfg = JDConfig(ini_file = None)
    cfg.env = None  # Make sure, we are not even trying to load an env file
    config_dir = data_dir("configs-2")
    data = cfg.load("main_config.yaml", config_dir)
    assert data
    assert len(cfg.files_loaded) == 4
    assert cfg.files_loaded[0].parts[-2:] == ("configs-2", "main_config.yaml")
    assert len(cfg.file_recursions) == 0

    monkeypatch.setenv('DB_USER', 'dbuser')
    monkeypatch.setenv('DB_PASS', 'dbpass')
    monkeypatch.setenv('DB_NAME', 'dbname')

    assert re.match(r"\d{8}-\d{6}", cfg.get("timestamp"))
    assert cfg.get("db") == "oracle"
    assert cfg.get("database.DB_USER") == "dbuser"
    assert cfg.get("database.DB_PASS") == "dbpass"
    assert cfg.get("database.DB_NAME") == "dbname"
    assert cfg.get("database.connection_string") == "oracle:dbuser/dbpass@dbname"

    assert cfg.get("debug.log_progress_after") == 20_000


@dataclass
class MyBespokePlaceholder(Placeholder):
    """This is also a test for a placeholder that does not take any parameters"""

    def resolve(self, _) -> str:
        return "value"

def test_add_placeholder():
    cfg = JDConfig(ini_file = None)
    cfg.register_placeholder("bespoke", MyBespokePlaceholder)

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

    cfg = JDConfig(ini_file = None)
    config_dir = data_dir("configs-3")

    with pytest.raises(ConfigException):
        cfg.load("config.yaml", config_dir)

    assert len(cfg.file_recursions) > 0


def test_import_replacement():
    config_dir = data_dir("configs-4")

    # Default: False. Load into "b"
    cfg = JDConfig(ini_file = None)
    data = cfg.load("config-1.yaml", config_dir)
    assert data
    assert cfg.get("a") == "aa"
    assert cfg.get("b.ia") == "iaa"
    assert cfg.get("b.ib") == "ibb"

    # False. Load into "b"
    cfg = JDConfig(ini_file = None)
    data = cfg.load("config-2.yaml", config_dir)
    assert data
    assert cfg.get("a") == "aa"
    assert cfg.get("b.ia") == "iaa"
    assert cfg.get("b.ib") == "ibb"

    # True. Merge on root level
    cfg = JDConfig(ini_file = None)
    data = cfg.load("config-3.yaml", config_dir)
    assert data
    assert cfg.get("a") == "aa"
    assert cfg.get("ia") == "iaa"
    assert cfg.get("ib") == "ibb"
    assert cfg.get("b", None) == None   # Does not exist


def test_walk():
    cfg = JDConfig(ini_file = None)

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
    data.remove(NodeEvent(("a",), YamlObj(2, 12, "<file>", "aa")))
    data.remove(NodeEvent(("b", "b1", "c1"), YamlObj(5, 21, "<file>", "1cc")))
    data.remove(NodeEvent(("b", "b1", "c2"), YamlObj(6, 21, "<file>", "2cc")))
    data.remove(NodeEvent(("b", "b2"), YamlObj(7, 17, "<file>", 22)))


def test_load_jdconfig_2_with_env(monkeypatch):

    monkeypatch.setenv('DB_USER', 'dbuser')
    monkeypatch.setenv('DB_PASS', 'dbpass')
    monkeypatch.setenv('DB_NAME', 'dbname')

    cfg = JDConfig(ini_file = None)
    cfg.env = "jd_dev"  # Apply own env specific changes

    config_dir = data_dir("configs-2")
    data = cfg.load("main_config.yaml", config_dir)
    assert data
    assert len(cfg.files_loaded) == 5
    assert cfg.files_loaded[0].parts[-2:] == ("configs-2", "main_config.yaml")
    assert cfg.files_loaded[4].parts[-2:] == ("configs-2", "main_config-jd_dev.yaml")
    assert len(cfg.file_recursions) == 3

    assert re.match(r"\d{8}-\d{6}", cfg.get("timestamp"))
    assert cfg.get("db") == "mysql"
    assert cfg.get("database.driver") == "mysql"
    assert cfg.get("database.user") == "omry"
    assert cfg.get("database.password") == "secret"
    assert cfg.get("database.DB_USER", None) == None
    assert cfg.get("database.DB_PASS", None) == None
    assert cfg.get("database.DB_NAME", None) == None
    assert cfg.get("database.connection_string", None) == None

    assert cfg.get("debug.log_progress_after") == 20_000
