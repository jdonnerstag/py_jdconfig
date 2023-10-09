#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C
# pylint: disable=protected-access

import logging
from copy import deepcopy
from typing import List, Mapping, Sequence
from jd_config import ConfigGetter, ConfigException, ConfigPath
import pytest

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


DATA = dict(
    a="aa",
    b="bb",
    c=dict(
        c1="c11",
        c2=dict(c22="c222", c23=23, c24=24.24, c25=23_000, c26=True, C28=False),
        c3=[11, 22, 33, "4a", dict(c32="c322")],
    ),
)


def test_walk():
    data = deepcopy(DATA)

    def walk(obj, path):
        path = ConfigPath.normalize_path(path)
        return ConfigGetter()._walk(obj, path, False)

    _d, key = walk(data, "a")
    assert isinstance(_d, dict)
    assert isinstance(key, str)
    assert key == "a"
    assert _d[key] == "aa"

    _d, key = walk(data, "c.c1")
    assert _d[key] == "c11"

    _d, key = walk(data, "c.c2.c23")
    assert _d[key] == 23

    _d, key = walk(data, "c.c3[1]")
    assert _d[key] == 22

    _d, key = walk(data, "c.c3[4].c32")
    assert _d[key] == "c322"


def test_get():
    data = deepcopy(DATA)
    assert ConfigGetter().get(data, "a") == "aa"
    assert ConfigGetter().get(data, "c.c1") == "c11"
    assert ConfigGetter().get(data, "c.c2.c23") == 23
    assert ConfigGetter().get(data, "c.c3[1]") == 22
    assert ConfigGetter().get(data, "c.c3[4].c32") == "c322"

    assert ConfigGetter().get(data, "c.xxx", "abc") == "abc"
    assert ConfigGetter().get(data, "c.c3[99].a", 123) == 123

    with pytest.raises(ConfigException):
        ConfigGetter().get(data, "c.xxx")


def test_set():
    data = deepcopy(DATA)
    assert ConfigGetter().set(data, "add_x", "xx") is None
    assert ConfigGetter().get(data, "add_x") == "xx"
    assert ConfigGetter().set(data, "add_x", "yy") == "xx"

    assert ConfigGetter().set(data, "c.c3[0]", 100) == 11
    assert ConfigGetter().get(data, "c.c3[0]") == 100

    assert ConfigGetter().set(data, "c.c3[4].a", 200) is None
    assert ConfigGetter().get(data, "c.c3[4].a") == 200

    # Parts of the tree are missing
    with pytest.raises(ConfigException):
        ConfigGetter().set(data, "z.a.b", 11)

    assert ConfigGetter().set(data, "z.a.b", 11, create_missing=True) is None
    assert ConfigGetter().get(data, "z.a.b") == 11

    # 'a' is not a mapping. Even with create_missing, it will not change the structure
    with pytest.raises(ConfigException):
        ConfigGetter().set(data, "a.new", 11, create_missing=True, replace_path=False)

    ConfigGetter().set(data, "a.new", 11, create_missing=True, replace_path=True)
    assert ConfigGetter().get(data, "a.new") == 11

    # 'c.c3' is not a mapping. Even with create_missing, it will not change the structure
    with pytest.raises(ConfigException):
        ConfigGetter().set(data, "c.c3.a", 11, create_missing=True, replace_path=False)

    ConfigGetter().set(data, "c.c3.a", 11, create_missing=True, replace_path=True)
    assert ConfigGetter().get(data, "c.c3.a") == 11

    ConfigGetter().set(data, "x.a[0]", 22, create_missing=True)
    assert ConfigGetter().get(data, "x.a[0]") == 22

    # This won't work: {x: a: {0: ..}}  0 is not subscriptable
    with pytest.raises(ConfigException):
        ConfigGetter().set(data, "x.a[0].b", 22, create_missing=True)

    def missing_1(_data: Mapping | Sequence, key: str | int, _):
        if key == "a":
            return [None] * 1

        return {}

    assert ConfigGetter().set(data, "y.a[0]", 12, create_missing=missing_1) is None
    assert ConfigGetter().get(data, "y.a[0]") == 12

    assert (
        ConfigGetter().set(data, "w.a[0]", 13, create_missing={"a": [None] * 1}) is None
    )
    assert ConfigGetter().get(data, "w.a[0]") == 13

    # My preference and most easiest way
    assert ConfigGetter().set(data, "v.a[0].b", 14, create_missing={"a": [{}]}) is None
    assert ConfigGetter().get(data, "v.a[0].b") == 14

    with pytest.raises(ConfigException):
        ConfigGetter().set(data, "v.a[0].b", 99, replace_value=False)

    assert ConfigGetter().set(data, "v.a[0].b", 99, replace_value=True) == 14
    assert ConfigGetter().get(data, "v.a[0].b") == 99


def test_delete():
    data = deepcopy(DATA)
    assert ConfigGetter().delete(data, "a") == "aa"
    assert ConfigGetter().delete(data, "does-not-exist", exception=False) is None

    with pytest.raises(ConfigException):
        ConfigGetter().delete(data, "does-not-exist", exception=True)

    assert ConfigGetter().delete(data, "c.c3[4].c32") == "c322"

    assert isinstance(ConfigGetter().delete(data, "c.c3[4]"), Mapping)
    assert len(ConfigGetter().get(data, "c.c3")) == 4

    assert isinstance(ConfigGetter().delete(data, "c.c3"), List)
    assert ConfigGetter().get(data, "c.c3", None) is None

    assert ConfigGetter().delete(data, "c")
    assert ConfigGetter().get(data, "b") == "bb"
    assert ConfigGetter().get(data, "c", None) is None


def test_get_path():
    data = deepcopy(DATA)
    assert ConfigGetter()._get_path(data, "c.c2.c25") == ("c", "c2", "c25")
    assert ConfigGetter()._get_path(data, "c..c25") == ("c", "c2", "c25")
    assert ConfigGetter()._get_path(data, "c..c2.c25") == ("c", "c2", "c25")
    assert ConfigGetter()._get_path(data, "c.*.c25") == ("c", "c2", "c25")
    assert ConfigGetter()._get_path(data, "*.*.c25") == ("c", "c2", "c25")
    assert ConfigGetter()._get_path(data, "..c25") == ("c", "c2", "c25")

    assert ConfigGetter()._get_path(data, "c.c3[0]") == ("c", "c3", 0)
    assert ConfigGetter()._get_path(data, "c.c3[4].c32") == ("c", "c3", 4, "c32")
    assert ConfigGetter()._get_path(data, "c.c3[*].c32") == ("c", "c3", 4, "c32")
    assert ConfigGetter()._get_path(data, "c.*.c32") == ("c", "c3", 4, "c32")
    assert ConfigGetter()._get_path(data, "c..c32") == ("c", "c3", 4, "c32")
    assert ConfigGetter()._get_path(data, "..c32") == ("c", "c3", 4, "c32")


def test_find():
    data = deepcopy(DATA)
    assert ConfigGetter().get(data, "c..c25") == 23_000
    assert ConfigGetter().get(data, "c.*.c32") == "c322"


def test_deep_update():
    data_1 = deepcopy(DATA)  #
    updates = {"a": "AA"}
    assert ConfigGetter().deep_update(data_1, updates).get("a") == "AA"

    # See DeepDict for a more elegant approach
    updates = {"b": {"b1": "BB"}}
    assert ConfigGetter().deep_update(data_1, updates)["b"]["b1"] == "BB"

    updates = {"c": {"c2": {"c22": "C_222"}}}
    assert ConfigGetter().deep_update(data_1, updates)["c"]["c2"]["c22"] == "C_222"

    updates = {"z": "new"}
    assert ConfigGetter().deep_update(data_1, updates)["z"] == "new"

    # TODO We don't support delete. How to replace dicts and lists, vs. values only?
    updates = {"b": {"b1": {"b2": "B222B"}}}
    assert ConfigGetter().deep_update(data_1, updates)["b"]["b1"] == {"b2": "B222B"}

    updates = {"b": {"b1": [1, 2, 3, 4]}}
    assert ConfigGetter().deep_update(data_1, updates)["b"]["b1"] == [1, 2, 3, 4]

    # Deliberately not supported
    # updates = {"c": {"c3": [None, 220]}}
    # assert ConfigGetter().deep_update(data_1, updates)["c"]["c3"][1] == 220

    # Deliberately not supported
    # updates = {"c": {"c3": [None, None, None, None, {"c33": "C_333"}]}}
    # assert ConfigGetter().deep_update(data_1, updates)["c"]["c3"][4]["C33"] == "C_333"

    # Deliberately not supported
    # It is possible to use deep find pattern as well, which is quite nice
    # updates = {"c.c3[*].c32": "C_321"}
    # assert ConfigGetter().deep_update(data_1, updates)["c"]["c3"][4]["C32"] == "C_321"

    # Deliberately not supported
    # updates = {"$delete$": ["c.c3[*].c32"]}
    # assert ConfigGetter().deep_update(data_1, updates)["c"]["c3"][4]["C32"] == "C_321"

    # Deliberately not supported
    # updates = {"$delete$": ["c.c3[2]"]}
    # assert ConfigGetter().deep_update(data_1, updates)["c"]["c3"][4]["C32"] == "C_321"

    # Deliberately not supported
    # updates = {"a": "$delete$"}
    # assert ConfigGetter().deep_update(data_1, updates)["c"]["c3"][4]["C32"] == "C_321"


# TODO we have not test (get, set, etc.) for lists in lists
