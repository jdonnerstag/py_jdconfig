#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
import os
import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from datetime import datetime
from typing import ForwardRef, Optional

import pytest

from jd_config import JDConfig, Placeholder
from jd_config.config_path import CfgPath
from jd_config.field import Field
from jd_config.resolvable_base_model import ResolvableBaseModel

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args) -> Path:
    return Path(os.path.join(os.path.dirname(__file__), "data", *args))


class Config1Schemata(ResolvableBaseModel):
    engine: str
    maintenance: str
    e2e: str


class Config1(ResolvableBaseModel):
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    connection_string: str
    db_job_name: str

    batch_size: int

    schematas: Config1Schemata


def test_load_jdconfig_1():
    # config-1 contains a simple config file, with no imports.

    cfg = JDConfig(Config1, ini_file=None)
    cfg.ini.config_dir = data_dir("configs-1")
    cfg.ini.config_file = "config.yaml"
    cfg.ini.default_env = "dev"

    data = cfg.load()
    assert data

    # Provide the config file name. Note, that it'll not change or set the
    # config_dir. Any config files imported, are imported relativ to the
    # config_dir configured (or preset) in config.ini
    cfg = JDConfig(Config1, ini_file=None)
    file = data_dir("configs-1", "config.yaml")
    data = cfg.load(file)
    assert data

    # Provide a filename and a config_dir. Any config files imported, are
    # still imported relativ to the config_dir configured (or preset) in
    # config.ini. The config_dir parameter provided, will only be used for
    # this one file. The config file might still be relativ or absolut.
    cfg = JDConfig(Config1, ini_file=None)
    config_dir = data_dir("configs-1")
    data = cfg.load("config.yaml", config_dir)
    assert data

    file = data_dir("configs-1", "config.yaml")
    data = cfg.load(file.absolute(), config_dir)
    assert data


def test_jdconfig_1_placeholders(monkeypatch):
    cfg = JDConfig(Config1, ini_file=None)
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


class Config4(ResolvableBaseModel):
    a: str
    b: str
    c: "Config4"
    d: str
    e: str
    f: str


def test_load_jdconfig_4():
    # config-4 is about simple {import:}, {ref:} and {global:}

    cfg = JDConfig(Config4, ini_file=None)
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


class Config2LoggingFormatters(ResolvableBaseModel):
    format: str


class Config2LoggingHandler(ResolvableBaseModel):
    class_: str = Field(name="class")
    level: str
    formatter: str
    stream: Optional[str] = None  # Add test case in BaseModel
    filename: str | None = None  # Add test case in BaseModel
    encoding: str = "utf8"


class Config2LoggingRoot(ResolvableBaseModel):
    level: str
    handlers: list[str]


class Config2Logging(ResolvableBaseModel):
    version: int
    disable_existing_loggers: bool
    log_dir: str
    timestamp: datetime

    formatters: dict[str, Config2LoggingFormatters]
    handlers: dict[str, Config2LoggingHandler]


class Config2Debug(ResolvableBaseModel):
    log_progress_after: int
    stop_after: int = 99_999


class Config2Mysql(ResolvableBaseModel):
    driver: str
    user: str
    password: str


class Config2Oracle(Config1):
    pass


class Config2Git(ResolvableBaseModel):
    git_exe: str
    pull_all_script: str


class Config2(ResolvableBaseModel):
    version: str
    timestamp: datetime

    db: str
    database: Config2Mysql | Config2Oracle
    git: Config2Git
    log_dir: str
    logging: Config2Logging

    debug: Config2Debug


def test_load_jdconfig_2(monkeypatch):
    # config-2 is using some import placeholders, including dynamic ones,
    # where the actually path refers to config value.

    cfg = JDConfig(Config2, ini_file=None)
    cfg.ini.env = None  # Make sure, we are not even trying to load an env file
    # config-2 has imports. Make sure, it is available for imports.
    cfg.ini.config_dir = data_dir("configs-2")
    # if config_dir provided to load() it is only used for this one file
    data = cfg.load("main_config.yaml")
    assert data

    # After loading the data. It works because we lazy resolve placeholders
    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    assert re.match(r"\d{8}-\d{6}", cfg.get("timestamp"))
    assert cfg.get("db") == "oracle"
    assert isinstance(cfg.get("database"), Config2Oracle)
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


class A(ResolvableBaseModel):
    a: str
    b: str
    c: str


def test_add_placeholder():
    cfg = JDConfig(A, ini_file=None)
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


Config3 = ForwardRef("Config3")


class Config3_3(ResolvableBaseModel):
    a3: str = Field(name="3a")
    b3: Config3 = Field(name="3b")


class Config3_2(ResolvableBaseModel):
    a2: str = Field(name="2a")
    b2: Config3_3 = Field(name="2b")


class Config3(ResolvableBaseModel):
    a1: str = Field(name="1a")
    b1: Config3_2 = Field(name="1b")
    c1: str = Field(name="1c", default="cc1")


def test_load_jdconfig_3():
    # config-3 has a file recursion

    cfg = JDConfig(Config3, ini_file=None)
    cfg.ini.config_dir = data_dir("configs-3")

    # Since we lazy resolve, loading the main file will not raise an exception
    data = cfg.load("config.yaml")

    assert data.a1 == "a"
    assert data.b1.a2 == "aa"
    assert data.b1.b2.a3 == "aaa"
    assert data.b1.b2.b3.a1 == "a"

    # with pytest.raises(ConfigException):
    # Recursion with imports in between
    assert isinstance(data.b1.b2.b3.b1, Config3_2)


def test_load_jdconfig_2_with_env(monkeypatch):
    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    cfg = JDConfig(Config2, ini_file=None)
    cfg.ini.env = "jd_dev"  # Apply own env specific changes
    cfg.ini.config_dir = data_dir("configs-2")
    data = cfg.load("main_config.yaml")
    assert data

    # Just the main config and its overlay file.
    assert len(cfg.files_loaded) == 2
    # Since we lazy resolve, run to_dict() ones to touch very attribute ones.
    data.to_dict()
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


class Config6(ResolvableBaseModel):
    a: str
    b: str
    c: "Config6"
    d: str
    e: str
    f: str


def test_separate_env_dir():
    # Config-6 is all about env specific overlay files.

    cfg = JDConfig(Config6, ini_file=None)
    cfg.ini.env = None  # Make sure, we are not even trying to load an env file
    cfg.ini.config_dir = data_dir("configs-6")
    assert cfg.ini.add_env_dirs == [Path.cwd()]

    cfg_file = Path("config.yaml")

    data = cfg.load(cfg_file)
    assert data
    assert data.__model_meta__
    assert data.__model_meta__.file.name.parts[-1] == "config.yaml"
    assert data.__model_meta__.file == data.__model_meta__.root
    assert data.__model_meta__.data.file_1.parts[-1] == "config.yaml"
    assert data.__model_meta__.data.file_2 is None

    data = data.get("c")
    assert data
    assert data.__model_meta__
    assert data.__model_meta__.file.name.parts[-1] == "config-2.yaml"
    assert data.__model_meta__.root.name.parts[-1] == "config.yaml"
    assert data.__model_meta__.data.file_1.parts[-1] == "config-2.yaml"
    assert data.__model_meta__.data.file_2 is None
    data = data.__model_meta__.parent.__model_meta__.data
    assert data.file_1.parts[-1] == "config.yaml"
    assert data.file_2 is None

    cfg.ini.env = "dev"
    data = cfg.load(cfg_file)
    assert data
    assert data.__model_meta__
    assert data.__model_meta__.file.name.parts[-1] == "config.yaml"
    assert data.__model_meta__.root.name.parts[-1] == "config.yaml"
    assert data.__model_meta__.data.file_1.parts[-1] == "config.yaml"
    assert data.__model_meta__.data.file_2.parts[-1] == "config-dev.yaml"

    data = data.get("c")
    assert data
    assert data.__model_meta__
    assert data.__model_meta__.file.name.parts[-1] == "config-2.yaml"
    assert data.__model_meta__.root.name.parts[-1] == "config.yaml"
    assert data.__model_meta__.data.file_1.parts[-1] == "config-2.yaml"
    assert data.__model_meta__.data.file_2 is None
    data = data.__model_meta__.parent.__model_meta__.data
    assert data.file_1.parts[-1] == "config.yaml"
    assert data.file_2.parts[-1] == "config-dev.yaml"

    cfg.ini.env = "qa"
    data = cfg.load(cfg_file)
    assert data
    assert data.__model_meta__
    assert data.__model_meta__.file.name.parts[-1] == "config.yaml"
    assert data.__model_meta__.file == data.__model_meta__.root
    assert data.__model_meta__.data.file_1.parts[-1] == "config.yaml"
    assert data.__model_meta__.data.file_2 is None

    data = data.get("c")
    assert data
    assert data.__model_meta__
    assert data.__model_meta__.file.name.parts[-1] == "config-2.yaml"
    assert data.__model_meta__.root.name.parts[-1] == "config.yaml"
    assert data.__model_meta__.data.file_1.parts[-1] == "config-2.yaml"
    assert data.__model_meta__.data.file_2.parts[-1] == "config-2-qa.yaml"
    data = data.__model_meta__.parent.__model_meta__.data
    assert data.file_1.parts[-1] == "config.yaml"
    assert data.file_2 is None

    cfg.ini.env = "dev-2"
    data = cfg.load(cfg_file)
    assert data
    assert data.__model_meta__
    assert data.__model_meta__.file.name.parts[-1] == "config.yaml"
    assert data.__model_meta__.file == data.__model_meta__.root
    assert data.__model_meta__.data.file_1.parts[-1] == "config.yaml"
    assert data.__model_meta__.data.file_2 is None

    data = data.get("c")
    assert data
    assert data.__model_meta__
    assert data.__model_meta__.file.name.parts[-1] == "config-2.yaml"
    assert data.__model_meta__.root.name.parts[-1] == "config.yaml"
    assert data.__model_meta__.data.file_1.parts[-1] == "config-2.yaml"
    assert data.__model_meta__.data.file_2 is None
    data = data.__model_meta__.parent.__model_meta__.data
    assert data.file_1.parts[-1] == "config.yaml"
    assert data.file_2 is None

    env_dir = Path(os.path.join(cfg.ini.config_dir, "env_files"))
    cfg.ini.add_env_dirs.append(env_dir)
    cfg.ini.env = "dev-2"
    data = cfg.load(cfg_file)
    assert data
    assert data.__model_meta__
    assert data.__model_meta__.file.name.parts[-1] == "config.yaml"
    assert data.__model_meta__.file == data.__model_meta__.root
    assert data.__model_meta__.data.file_1.parts[-1] == "config.yaml"
    assert data.__model_meta__.data.file_2.parts[-1] == "config-dev-2.yaml"

    data = data.get("c")
    assert data
    assert data.__model_meta__
    assert data.__model_meta__.file.name.parts[-1] == "config-2.yaml"
    assert data.__model_meta__.root.name.parts[-1] == "config.yaml"
    assert data.__model_meta__.data.file_1.parts[-1] == "config-2.yaml"
    assert data.__model_meta__.data.file_2 is None
    data = data.__model_meta__.parent.__model_meta__.data
    assert data.file_1.parts[-1] == "config.yaml"
    assert data.file_2.parts[-1] == "config-dev-2.yaml"


def test_to_dict(monkeypatch):
    # config-2 is using some import placeholders, including dynamic ones,
    # where the actually path refers to config value.

    cfg = JDConfig(Config2, ini_file=None)
    cfg.ini.env = None  # Make sure, we are not even trying to load an env file
    # config-2 has imports. Make sure, it is available for imports.
    cfg.ini.config_dir = data_dir("configs-2")
    # if config_dir provided to load() it is only used for this one file
    data = cfg.load("main_config.yaml")
    assert data

    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    data = cfg.config().to_dict()
    assert data["db"] == "oracle"
    assert data["database"]["DB_USER"] == "dbuser"
    assert data["database"]["DB_PASS"] == "dbpass"
    assert data["database"]["DB_NAME"] == "dbname"
    assert data["database"]["connection_string"] == "oracle:dbuser/dbpass@dbname"
    assert data["debug"]["log_progress_after"] == 20_000


def test_path_separator():
    # Validate it is still working in main config level
    # config-4 is about simple {import:}, {ref:} and {global:}

    cfg = JDConfig(Config4, ini_file=None)
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
