#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from dataclasses import dataclass
from io import StringIO
import logging
import os
from pathlib import Path
import re
from typing import Mapping

import pytest
from jd_config import RefPlaceholder, ImportPlaceholder, EnvPlaceholder, YamlObj
from jd_config import ResolverMixin, DeepAccessMixin, ConfigFileLoader
from jd_config import ConfigException, Placeholder, NodeEvent

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_ImportPlaceholder():
    obj = ImportPlaceholder(file="xxx")
    assert obj.file == "xxx"

    # Filename is missing
    with pytest.raises(Exception):
        ImportPlaceholder(file="")


def test_RefPlaceholder():
    obj = RefPlaceholder(path="db")
    assert obj.path == "db"
    assert obj.default_val is None

    # Filename is missing
    with pytest.raises(Exception):
        RefPlaceholder(path="")


def test_EnvPlaceholder():
    obj = EnvPlaceholder(env_var="ENV")
    assert obj.env_var == "ENV"
    assert obj.default_val is None

    # Filename is missing
    with pytest.raises(Exception):
        EnvPlaceholder(env_var="")


def test_post_load_and_resolve():
    # "db-a" is the reference we want to resolve. "db-a" occurs in the db yaml file,
    # as well as the main yaml file.
    # We want the resolver to first try against the the yaml file which contains the {ref:..},
    # and only if not found, try from the very root.

    placeholder_db_a = RefPlaceholder("db-a")
    placeholder_a = RefPlaceholder("a")

    # Simulate a db yaml file
    cfg_db = {
        "db-a": YamlObj(0, 0, None, "db-a1"),
        "db-b": YamlObj(0, 0, None, [placeholder_db_a]),
        "db-c": YamlObj(0, 0, None, [placeholder_a]),
    }

    # Simulate the main yaml file, which has imported the db yaml file.
    # Both files contain a "db-a" key.
    cfg = {
        "a": YamlObj(0, 0, None, 11),
        "db": cfg_db,
        "db-a": YamlObj(0, 0, None, "from root"),
    }

    # First placeholder.post_load() was not invoked, so that RefPlaceholder does
    # not know about the root obj of the db yaml file.
    assert placeholder_db_a.file_root is None
    assert placeholder_db_a.resolve(cfg) == "from root"  # From the main yaml file

    # Invoke post_load() as JDConfig.load() will do, and register the db yaml
    # file obj with the placeholder. This way, placeholder.resolve() can leverage
    # it to resolve in 2 steps: step 1: db yaml file; step 2: main yaml file.
    placeholder_db_a.post_load(cfg_db)
    assert placeholder_db_a.file_root is not None
    assert placeholder_db_a.resolve(cfg) == "db-a1"

    # This placeholder will fail resolving in the db yaml file, but succeed in
    # the main yaml file.
    placeholder_a.post_load(cfg_db)
    assert placeholder_a.file_root is not None
    assert placeholder_a.resolve(cfg) == 11

    # Simulate an env yaml file
    env_cfg = {
        "a": YamlObj(0, 0, None, 11),
        "db": cfg_db,
        "db-a": YamlObj(0, 0, None, "env file"),
    }

    placeholder_db_a.post_load(cfg_db)
    assert placeholder_db_a.file_root is not None
    assert placeholder_db_a.resolve(cfg, env_cfg) == "env file"


class MyMixinTestClass(ResolverMixin, DeepAccessMixin):
    def __init__(self) -> None:
        self.data = None

        ResolverMixin.__init__(self)
        DeepAccessMixin.__init__(self)

        # Why this approach and not a Mixin/Base Class. ConfigFileLoader
        # is comparatively large with a number of functions. Functions
        # which I consider private, but python has not means to mark them
        # private. This is a more explicit approach.
        self.config_file_loader = ConfigFileLoader(dependencies=self)

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


def test_jd_config_1_mandatory_values():
    cfg = MyMixinTestClass()
    data = cfg.load(Path("config.yaml"), config_dir=data_dir("configs-1"))
    assert data

    # Should fail, as value is marked mandatory with ???
    with pytest.raises(ConfigException):
        cfg.get("DB_USER")

    # Providing a default will not help. ??? Mandates a config value.
    # get(.., <default>) only applies to missing keys. But DB_USER exists.
    with pytest.raises(ConfigException):
        cfg.get("DB_USER", "xxx")

    # Should fail, as value is marked mandatory with ???
    with pytest.raises(ConfigException):
        cfg.get("DB_PASS")

    # DB_NAME has a default configure in the the yaml file.
    assert cfg.get("DB_NAME") == "my_default_db"


def test_jdconfig_1_placeholders(monkeypatch):
    cfg = MyMixinTestClass()
    data = cfg.load(Path("config.yaml"), data_dir("configs-1"))
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


def test_load_jdconfig_2(monkeypatch):
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

    monkeypatch.setenv("DB_USER", "dbuser")
    monkeypatch.setenv("DB_PASS", "dbpass")
    monkeypatch.setenv("DB_NAME", "dbname")

    assert re.match(r"\d{8}-\d{6}", cfg.get("timestamp"))
    assert cfg.get("db") == "oracle"
    assert cfg.get("database.DB_USER") == "dbuser"
    assert cfg.get("database.DB_PASS") == "dbpass"
    assert cfg.get("database.DB_NAME") == "dbname"
    assert cfg.get("database.connection_string") == "oracle:dbuser/dbpass@dbname"

    assert cfg.get("debug.log_progress_after") == 20_000


@dataclass
class MyBespokePlaceholder(Placeholder):
    # This is also a test for a placeholder that does not take any parameters

    def resolve(self, *_) -> str:
        return "value"


def test_add_placeholder():
    cfg = MyMixinTestClass()
    cfg.register_placeholder("bespoke", MyBespokePlaceholder)

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

    assert cfg.get("c") == "value"


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

    data = list(cfg.walk(resolve=True))
    assert len(data) == 4
    data.remove(NodeEvent(("a",), "aa"))
    data.remove(NodeEvent(("b", "b1", "c1"), "1cc"))
    data.remove(NodeEvent(("b", "b1", "c2"), "2cc"))
    data.remove(NodeEvent(("b", "b2"), 22))

    data = list(cfg.walk(resolve=False))
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
