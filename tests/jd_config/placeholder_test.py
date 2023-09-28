#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging

import pytest
from jd_config import RefPlaceholder, ImportPlaceholder, EnvPlaceholder, YamlObj

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
