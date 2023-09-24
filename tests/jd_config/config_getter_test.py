#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from typing import List, Mapping
from jd_config import ConfigGetter, ConfigException
import pytest

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG

def test_normalize_path():

    assert ConfigGetter.normalize_path("a", sep=".") == ["a"]
    assert ConfigGetter.normalize_path(1, sep=".") == [1]
    assert ConfigGetter.normalize_path(["a", 1], sep=".") == ["a", 1]
    assert ConfigGetter.normalize_path("a.b.c", sep=".") == ["a", "b", "c"]
    assert ConfigGetter.normalize_path("a[1].b", sep=".") == ["a", 1, "b"]
    assert ConfigGetter.normalize_path("a.1.b", sep=".") == ["a", 1, "b"]
    assert ConfigGetter.normalize_path("a/b/c", sep="/") == ["a", "b", "c"]
    assert ConfigGetter.normalize_path("[a][b][c]", sep=".") == ["a", "b", "c"]
    assert ConfigGetter.normalize_path(["a", "b", "c"], sep=".") == ["a", "b", "c"]
    assert ConfigGetter.normalize_path(("a", "b", "c",), sep=".") == ["a", "b", "c"]
    assert ConfigGetter.normalize_path(("a", "b.c",), sep=".") == ["a", "b", "c"]

DATA = dict(
    a = "aa",
    b = "bb",
    c = dict(
        c1 = "c11",
        c2 = dict(
            c22 = "c222",
            c23 = 23,
            c24 = 24.24,
            c25 = 23_000,
            c26 = True,
            C28 = False
        ),
        c3 = [
            11,
            22,
            33,
            "4a",
            dict(c32 = "c322")
        ]
    )
)

def test_walk():

    _d, key = ConfigGetter.walk(DATA, "a")
    assert isinstance(_d, dict)
    assert isinstance(key, str)
    assert key == "a"
    assert _d[key] == "aa"

    _d, key = ConfigGetter.walk(DATA, "c.c1")
    assert _d[key] == "c11"

    _d, key = ConfigGetter.walk(DATA, "c.c2.c23")
    assert _d[key] == 23

    _d, key = ConfigGetter.walk(DATA, "c.c3[1]")
    assert _d[key] == 22

    _d, key = ConfigGetter.walk(DATA, "c.c3[4].c32")
    assert _d[key] == "c322"

def test_get():
    assert ConfigGetter.get(DATA, "a") == "aa"
    assert ConfigGetter.get(DATA, "c.c1") == "c11"
    assert ConfigGetter.get(DATA, "c.c2.c23") == 23
    assert ConfigGetter.get(DATA, "c.c3[1]") == 22
    assert ConfigGetter.get(DATA, "c.c3[4].c32") == "c322"

    assert ConfigGetter.get(DATA, "c.xxx", "abc") == "abc"
    assert ConfigGetter.get(DATA, "c.c3[99].a", 123) == 123

    with pytest.raises(ConfigException):
        ConfigGetter.get(DATA, "c.xxx")

def test_set():
    assert ConfigGetter.set(DATA, "add_x", "xx") == None
    assert ConfigGetter.get(DATA, "add_x") == "xx"
    assert ConfigGetter.set(DATA, "add_x", "yy") == "xx"

    assert ConfigGetter.set(DATA, "c.c3[0]", 100) == 11
    assert ConfigGetter.get(DATA, "c.c3[0]") == 100

    assert ConfigGetter.set(DATA, "c.c3[4].a", 200) == None
    assert ConfigGetter.get(DATA, "c.c3[4].a") == 200

def test_delete():
    assert ConfigGetter.delete(DATA, "a") == "aa"
    assert ConfigGetter.delete(DATA, "does-not-exist", exception=False) == None

    with pytest.raises(ConfigException):
        ConfigGetter.delete(DATA, "does-not-exist", exception=True)

    assert ConfigGetter.delete(DATA, "c.c3[4].c32") == "c322"

    assert isinstance(ConfigGetter.delete(DATA, "c.c3[4]"), Mapping)
    assert len(ConfigGetter.get(DATA, "c.c3")) == 4

    assert isinstance(ConfigGetter.delete(DATA, "c.c3"), List)
    assert ConfigGetter.get(DATA, "c.c3", None) == None

    assert ConfigGetter.delete(DATA, "c")
    assert ConfigGetter.get(DATA, "b") == "bb"
    assert ConfigGetter.get(DATA, "c", None) == None
