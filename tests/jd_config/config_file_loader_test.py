#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from dataclasses import dataclass
from io import StringIO
import os
from pathlib import Path
import logging
from typing import Mapping
import pytest
from jd_config import Placeholder, ConfigException, YamlObj, NodeEvent, ConfigFileLoader
from jd_config import ResolverMixin, EnvPlaceholder, RefPlaceholder
from jd_config import TimestampPlaceholder, ObjectWalker


logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class MyMixinTestClass(ResolverMixin):
    def __init__(self) -> None:
        self.data = None

        ResolverMixin.__init__(self)

        # Why this approach and not a Mixin/Base Class. ConfigFileLoader
        # is comparatively large with a number of functions. Functions
        # which I consider private, but python has not means to mark them
        # private. This is a more explicit approach.
        self.config_file_loader = ConfigFileLoader(dependencies=self)

    # TODO This is repetitive => create a little mixin
    def load(
        self, fname: Path | StringIO, config_dir: Path | None, env: str | None = None
    ) -> Mapping:
        self.data = self.config_file_loader.load(fname, config_dir, env)
        return self.data

    @property
    def files_loaded(self):
        return self.config_file_loader.files_loaded

    @property
    def file_recursions(self):
        return self.config_file_loader.file_recursions


def data_dir(*args) -> Path:
    path = os.path.join(os.path.dirname(__file__), "data", *args)
    path = Path(path).relative_to(Path.cwd())
    return path


def test_load_jdconfig_1():
    # config-1 contains a simple config file, with no imports.

    cfg = MyMixinTestClass()
    data = cfg.load(Path("config.yaml"), config_dir=data_dir("configs-1"))
    assert data
    assert len(cfg.files_loaded) == 1
    assert cfg.files_loaded[0].parts[-2:] == ("configs-1", "config.yaml")
    assert len(cfg.file_recursions) == 0

    # With an absolute filename, the config_dir is ignored. Which however
    # only works as long as not {import: ..} placeholders are used.
    cfg = MyMixinTestClass()
    file = data_dir("configs-1", "config.yaml")
    data = cfg.load(file.absolute(), config_dir=Path("/this/likely/does/not/exist"))
    assert data

    # It shouldn't matter
    data = cfg.load(file.absolute(), config_dir=None)
    assert data

    assert data["DB_USER"].file.parts[-2:] == ("configs-1", "config.yaml")
    assert data["DB_USER"].value == [EnvPlaceholder("DB_USER", "???")]
    assert data["DB_PASS"].value == [EnvPlaceholder("DB_PASS", "???")]
    assert data["DB_NAME"].value == [EnvPlaceholder("DB_NAME", "my_default_db")]


def test_load_jdconfig_2_and_post_load():
    # config-2 is using some import placeholders, including dynamic ones,
    # where the actually path refers to config value.

    # Apply config_dir to set working directory for relativ yaml imports
    # Test explicitly w/o env. There is another test to test with env
    cfg = MyMixinTestClass()
    data = cfg.load(Path("main_config.yaml"), data_dir("configs-2"), env=None)
    assert data
    assert len(cfg.files_loaded) == 4
    assert cfg.files_loaded[0].parts[-2:] == ("configs-2", "main_config.yaml")
    assert len(cfg.file_recursions) == 0

    assert data["db"].file.parts[-2:] == ("configs-2", "main_config.yaml")
    assert data["db"].value == "oracle"

    assert data["timestamp"].value == [TimestampPlaceholder("%Y%m%d-%H%M%S")]

    assert data["database"]["DB_USER"].value == [EnvPlaceholder("DB_USER", "???")]
    assert data["database"]["DB_PASS"].value == [EnvPlaceholder("DB_PASS", "???")]
    assert data["database"]["DB_NAME"].value == [EnvPlaceholder("DB_NAME", "???")]
    assert data["database"]["connection_string"].value == [
        # Add data["database"] is a post_load() activity
        RefPlaceholder("db", None, data["database"]),
        ":",
        RefPlaceholder("DB_USER", None, data["database"]),
        "/",
        RefPlaceholder("DB_PASS", None, data["database"]),
        "@",
        RefPlaceholder("DB_NAME", None, data["database"]),
    ]

    assert data["debug"]["log_progress_after"].value == 20_000


@dataclass
class MyBespokePlaceholder(Placeholder):
    """This is also a test for a placeholder that does not take any parameters"""

    def resolve(self, *_) -> str:
        return "value"


def test_add_placeholder():
    # Validate that we are able to register new placeholders, and that, upon load,
    # they properly parsed and replaced.

    cfg = MyMixinTestClass()
    cfg.register_placeholder_handler("bespoke", MyBespokePlaceholder)

    DATA = """
        a: aa
        b: bb
        c: '{bespoke:}'
    """

    file_like_io = StringIO(DATA)
    data = cfg.load(file_like_io, None)
    assert data

    assert len(cfg.files_loaded) == 1
    assert cfg.files_loaded[0] == "<data>"

    assert data["a"].value == "aa"
    assert data["c"].value == [MyBespokePlaceholder()]


def test_load_jdconfig_3():
    # config-3 has a file recursion
    cfg = MyMixinTestClass()
    with pytest.raises(ConfigException):
        cfg.load(Path("config.yaml"), data_dir("configs-3"))

    assert len(cfg.file_recursions) > 0


def test_walk():
    cfg = MyMixinTestClass()

    DATA = """
        a: aa
        b:
            b1:
                c1: "1cc"
                c2: "2cc"
            b2: 22
    """

    file_like_io = StringIO(DATA)
    data = cfg.load(file_like_io, None)
    assert data

    data = list(ObjectWalker.objwalk(data, nodes_only=True))
    assert len(data) == 4
    data.remove(NodeEvent(("a",), YamlObj(2, 12, Path("<file>"), "aa")))
    data.remove(NodeEvent(("b", "b1", "c1"), YamlObj(5, 21, Path("<file>"), "1cc")))
    data.remove(NodeEvent(("b", "b1", "c2"), YamlObj(6, 21, Path("<file>"), "2cc")))
    data.remove(NodeEvent(("b", "b2"), YamlObj(7, 17, Path("<file>"), 22)))


def test_load_jdconfig_2_with_env(monkeypatch):
    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    cfg = MyMixinTestClass()
    data = cfg.load(Path("main_config.yaml"), data_dir("configs-2"), env="jd_dev")
    assert data
    assert len(cfg.files_loaded) == 5
    assert cfg.files_loaded[0].parts[-2:] == ("configs-2", "main_config.yaml")
    assert cfg.files_loaded[1].parts[-2:] == ("configs-2", "main_config-jd_dev.yaml")
    assert len(cfg.file_recursions) == 0

    assert data["db"].file.parts[-2:] == ("configs-2", "main_config-jd_dev.yaml")
    assert data["db"].value == "mysql"

    assert data["database"]["driver"].file.parts[-2:] == ("db", "mysql_config.yaml")

    assert data["database"]["driver"].value == "mysql"
    assert data["database"]["user"].value == "omry"
    assert data["database"]["password"].value == "secret"

    assert "DB_USER" not in data["database"]
    assert "DB_PASS" not in data["database"]
    assert "DB_NAME" not in data["database"]
    assert "connection_string" not in data["database"]
    assert data["debug"]["log_progress_after"].value == 20_000
