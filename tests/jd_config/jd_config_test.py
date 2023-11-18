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
from jd_config.config_path import CfgPath

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args) -> Path:
    return Path(os.path.join(os.path.dirname(__file__), "data", *args))


def test_load_jdconfig_1():
    # config-1 contains a simple config file, with no imports.

    cfg = JDConfig(ini_file=None)
    cfg.ini.config_dir = data_dir("configs-1")
    cfg.ini.config_file = "config.yaml"
    cfg.ini.default_env = "dev"

    data = cfg.load()
    assert data

    # Provide the config file name. Note, that it'll not change or set the
    # config_dir. Any config files imported, are imported relativ to the
    # config_dir configured (or preset) in config.ini
    cfg = JDConfig(ini_file=None)
    file = data_dir("configs-1", "config.yaml")
    data = cfg.load(file)
    assert data

    # Provide a filename and a config_dir. Any config files imported, are
    # still imported relativ to the config_dir configured (or preset) in
    # config.ini. The config_dir parameter provided, will only be used for
    # this one file. The config file might still be relativ or absolut.
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
    # config-4 is about simple {import:}, {ref:} and {global:}

    cfg = JDConfig(ini_file=None)
    cfg.ini.env = None  # Make sure, we are not even trying to load an env file
    cfg.ini.config_dir = data_dir("configs-4")  # configure the directory for imports
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

    with pytest.raises(KeyError):
        cfg.get("g")


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
    cfg.placeholder_registry["bespoke"] = MyBespokePlaceholder

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
    cfg.ini.config_dir = data_dir("configs-3")

    # Since we lazy resolve, loading the main file will not raise an exception
    cfg.load("config.yaml")

    assert cfg.get("1a") == "a"
    assert cfg.get("1b.2a") == "aa"
    assert cfg.get("1b.2b.3a") == "aaa"
    assert cfg.get("1b.2b.3b.1a") == "a"

    with pytest.raises(ConfigException):
        # Recursion with imports in between
        cfg.get("1b.2b.3b.1b")


def test_walk():
    cfg = JDConfig(ini_file=None)

    DATA = """
        a: aa
        b:
            b1:
                c1: "{ref:a}"
                c2: "2cc"
            b2: 22
    """

    file_like_io = StringIO(DATA)
    data = cfg.load(file_like_io)
    assert data

    data = list(cfg.walk(nodes_only=True, resolve=True))
    assert len(data) == 4
    data.remove(NodeEvent(("a",), "aa", None))
    data.remove(NodeEvent(("b", "b1", "c1"), "aa", None))
    data.remove(NodeEvent(("b", "b1", "c2"), "2cc", None))
    data.remove(NodeEvent(("b", "b2"), 22, None))

    data = list(cfg.walk(nodes_only=True, resolve=False))
    assert len(data) == 4
    data.remove(NodeEvent(("a",), "aa", None))
    data.remove(NodeEvent(("b", "b1", "c1"), "{ref:a}", None))
    data.remove(NodeEvent(("b", "b1", "c2"), "2cc", None))
    data.remove(NodeEvent(("b", "b2"), 22, None))

    data = list(cfg.walk(nodes_only=False, resolve=True))
    assert len(data) == 8


def test_load_jdconfig_2_with_env(monkeypatch):
    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    cfg = JDConfig(ini_file=None)
    cfg.ini.env = "jd_dev"  # Apply own env specific changes
    cfg.ini.config_dir = data_dir("configs-2")
    data = cfg.load("main_config.yaml")
    assert data

    # Since we lazy resolve, run to_dict(resolve=True) ones
    cfg.to_dict(resolve=True)
    assert len(cfg.files_loaded) == 6
    assert cfg.files_loaded[0].parts[-2:] == ("configs-2", "main_config.yaml")
    assert cfg.files_loaded[1].parts[-2:] == ("configs-2", "main_config-jd_dev.yaml")

    assert re.match(r"\d{8}-\d{6}", cfg.get("timestamp"))
    assert cfg.get("db") == "mysql"
    assert cfg.get("database.driver") == "mysql"
    assert cfg.get("database.user") == "omry"
    assert cfg.get("database.password") == "another_secret"  # from the overlay
    assert cfg.get("database.DB_USER", None) is None
    assert cfg.get("database.DB_PASS", None) is None
    assert cfg.get("database.DB_NAME", None) is None
    assert cfg.get("database.connection_string", None) is None

    assert cfg.get("debug.log_progress_after") == 20_000


def test_resolve_all(monkeypatch):
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

    assert cfg.get("db", None, resolve=False) == "oracle"
    assert cfg.get("db", None, resolve=True) == "oracle"
    assert cfg.get("database.DB_USER", None, resolve=False) == None
    assert cfg.get("database.DB_USER", None, resolve=True) == "dbuser"
    assert cfg.get("database.DB_PASS", None, resolve=False) == None
    assert cfg.get("database.DB_PASS", None, resolve=True) == "dbpass"
    assert cfg.get("database.DB_NAME", None, resolve=False) == None
    assert cfg.get("database.DB_NAME", None, resolve=True) == "dbname"
    assert cfg.get("database.connection_string", None, resolve=False) == None
    assert (
        cfg.get("database.connection_string", resolve=True)
        == "oracle:dbuser/dbpass@dbname"
    )
    assert cfg.get("debug.log_progress_after", resolve=False) == 20_000
    assert cfg.get("debug.log_progress_after", resolve=True) == 20_000

    data = cfg.resolve_all()
    assert data

    assert cfg.get("db", resolve=False) == "oracle"
    assert cfg.get("db", resolve=True) == "oracle"
    assert cfg.get("database.DB_USER", resolve=False) == "dbuser"
    assert cfg.get("database.DB_USER", resolve=True) == "dbuser"
    assert cfg.get("database.DB_PASS", resolve=False) == "dbpass"
    assert cfg.get("database.DB_PASS", resolve=True) == "dbpass"
    assert cfg.get("database.DB_NAME", resolve=False) == "dbname"
    assert cfg.get("database.DB_NAME", resolve=True) == "dbname"
    assert (
        cfg.get("database.connection_string", resolve=False)
        == "oracle:dbuser/dbpass@dbname"
    )
    assert (
        cfg.get("database.connection_string", resolve=True)
        == "oracle:dbuser/dbpass@dbname"
    )
    assert cfg.get("debug.log_progress_after", resolve=False) == 20_000
    assert cfg.get("debug.log_progress_after", resolve=True) == 20_000


def test_separate_env_dir():
    # Config-6 is all about env specific overlay files.

    cfg = JDConfig(ini_file=None)
    cfg.ini.env = None  # Make sure, we are not even trying to load an env file
    cfg.ini.config_dir = data_dir("configs-6")
    assert cfg.ini.env_dirs == [Path.cwd()]

    cfg_file = Path("config.yaml")

    data = cfg.load(cfg_file)
    assert data  # DeepDict
    assert data.obj  # The ConfigFile object containing the DeepDict data
    assert data.obj.file_1.parts[-1] == "config.yaml"
    assert data.obj.file_2 is None
    assert data.obj.data_1
    assert data.obj.data_2 is None

    data = data.get("c")
    assert data  # DeepDict
    assert data.obj  # The ConfigFile object containing the DeepDict data
    assert data.obj.file_1.parts[-1] == "config-2.yaml"
    assert data.obj.file_2 is None
    assert data.obj.data_1
    assert data.obj.data_2 is None

    cfg.ini.env = "dev"
    data = cfg.load(cfg_file)
    assert data  # DeepDict
    assert data.obj  # The ConfigFile object containing the DeepDict data
    assert data.obj.file_1.parts[-1] == "config.yaml"
    assert data.obj.file_2.parts[-1] == "config-dev.yaml"
    assert data.obj.data_1
    assert data.obj.data_2

    data = data.get("c")
    assert data  # DeepDict
    assert data.obj  # The ConfigFile object containing the DeepDict data
    assert data.obj.file_1.parts[-1] == "config-2.yaml"
    assert data.obj.file_2 is None
    assert data.obj.data_1
    assert data.obj.data_2 is None

    cfg.ini.env = "qa"
    data = cfg.load(cfg_file)
    assert data  # DeepDict
    assert data.obj  # The ConfigFile object containing the DeepDict data
    assert data.obj.file_1.parts[-1] == "config.yaml"
    assert data.obj.file_2 is None
    assert data.obj.data_1
    assert data.obj.data_2 is None

    data = data.get("c")
    assert data  # DeepDict
    assert data.obj  # The ConfigFile object containing the DeepDict data
    assert data.obj.file_1.parts[-1] == "config-2.yaml"
    assert data.obj.file_2.parts[-1] == "config-2-qa.yaml"
    assert data.obj.data_1
    assert data.obj.data_2

    cfg.ini.env = "dev-2"
    data = cfg.load(cfg_file)
    assert data  # DeepDict
    assert data.obj  # The ConfigFile object containing the DeepDict data
    assert data.obj.file_1.parts[-1] == "config.yaml"
    assert data.obj.file_2 is None
    assert data.obj.data_1
    assert data.obj.data_2 is None

    data = data.get("c")
    assert data  # DeepDict
    assert data.obj  # The ConfigFile object containing the DeepDict data
    assert data.obj.file_1.parts[-1] == "config-2.yaml"
    assert data.obj.file_2 is None
    assert data.obj.data_1
    assert data.obj.data_2 is None

    env_dir = Path(os.path.join(cfg.ini.config_dir, "env_files"))
    cfg.ini.env_dirs.append(env_dir)
    data = cfg.load(cfg_file)
    assert data  # DeepDict
    assert data.obj  # The ConfigFile object containing the DeepDict data
    assert data.obj.file_1.parts[-1] == "config.yaml"
    assert data.obj.file_2.parts[-1] == "config-dev-2.yaml"
    assert data.obj.data_1
    assert data.obj.data_2

    data = data.get("c")
    assert data  # DeepDict
    assert data.obj  # The ConfigFile object containing the DeepDict data
    assert data.obj.file_1.parts[-1] == "config-2.yaml"
    assert data.obj.file_2 is None
    assert data.obj.data_1
    assert data.obj.data_2 is None


def test_path_separator():
    # Validate it is still working in main config level
    # config-4 is about simple {import:}, {ref:} and {global:}

    cfg = JDConfig(ini_file=None)
    cfg.ini.env = None  # Make sure, we are not even trying to load an env file
    cfg.ini.config_dir = data_dir("configs-4")  # configure the directory for imports
    data = cfg.load("config.yaml")
    assert data

    # Default: "."
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

    # Default: "."
    assert data.get(CfgPath("a")) == "aa"
    assert data.get(CfgPath("b")) == "aa"
    assert data.get(CfgPath("c"))
    assert data.get(CfgPath("c.a")) == "2aa"
    assert data.get(CfgPath("c.b")) == "2aa"
    assert data.get(CfgPath("c.c")) == "aa"
    assert data.get(CfgPath("c.d")) == "2aa"
    assert data.get(CfgPath("c.e")) == "aa"
    assert data.get(CfgPath("c.f")) == "aa"
    assert data.get(CfgPath("d")) == "2aa"
    assert data.get(CfgPath("e")) == "2aa"
    assert data.get(CfgPath("f")) == "aa"

    # Explicit: "."
    sep = "."
    assert data.get(CfgPath("a", sep=sep)) == "aa"
    assert data.get(CfgPath("b", sep=sep)) == "aa"
    assert data.get(CfgPath("c", sep=sep))
    assert data.get(CfgPath("c.a", sep=sep)) == "2aa"
    assert data.get(CfgPath("c.b", sep=sep)) == "2aa"
    assert data.get(CfgPath("c.c", sep=sep)) == "aa"
    assert data.get(CfgPath("c.d", sep=sep)) == "2aa"
    assert data.get(CfgPath("c.e", sep=sep)) == "aa"
    assert data.get(CfgPath("c.f", sep=sep)) == "aa"
    assert data.get(CfgPath("d", sep=sep)) == "2aa"
    assert data.get(CfgPath("e", sep=sep)) == "2aa"
    assert data.get(CfgPath("f", sep=sep)) == "aa"

    # Explicit: "/"
    # Note: this does not apply to {ref:..} which still use default "."
    sep = "/"
    assert data.get(CfgPath("a", sep=sep)) == "aa"
    assert data.get(CfgPath("b", sep=sep)) == "aa"
    assert data.get(CfgPath("c", sep=sep))
    assert data.get(CfgPath("c/a", sep=sep)) == "2aa"
    assert data.get(CfgPath("c/b", sep=sep)) == "2aa"
    assert data.get(CfgPath("c/c", sep=sep)) == "aa"
    assert data.get(CfgPath("c/d", sep=sep)) == "2aa"
    assert data.get(CfgPath("c/e", sep=sep)) == "aa"
    assert data.get(CfgPath("c/f", sep=sep)) == "aa"
    assert data.get(CfgPath("d", sep=sep)) == "2aa"
    assert data.get(CfgPath("e", sep=sep)) == "2aa"
    assert data.get(CfgPath("f", sep=sep)) == "aa"
