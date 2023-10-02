#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C
# pylint: disable=protected-access

from copy import deepcopy
import logging
from typing import List, Mapping, Sequence
from jd_config import ConfigGetter, ConfigException, DeepDict
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


def test_get():
    data = DeepDict(deepcopy(DATA))
    assert data.get("a") == "aa"
    assert data.get("c.c1") == "c11"
    assert data.get("c.c2.c23") == 23
    assert data.get("c.c3[1]") == 22
    assert data.get("c.c3[4].c32") == "c322"

    assert data.get("c.xxx", "abc") == "abc"
    assert data.get("c.c3[99].a", 123) == 123

    with pytest.raises(ConfigException):
        data.get("c.xxx")


def test_set():
    data = DeepDict(deepcopy(DATA))
    assert data.set("add_x", "xx") is None
    assert data.get("add_x") == "xx"
    assert data.set("add_x", "yy") == "xx"

    assert data.set("c.c3[0]", 100) == 11
    assert data.get("c.c3[0]") == 100

    assert data.set("c.c3[4].a", 200) is None
    assert data.get("c.c3[4].a") == 200

    # Parts of the tree are missing
    with pytest.raises(ConfigException):
        data.set("z.a.b", 11)

    assert data.set("z.a.b", 11, create_missing=True) is None
    assert data.get("z.a.b") == 11

    # 'a' is not a mapping. Even with create_missing, it will not change the structure
    with pytest.raises(ConfigException):
        data.set("a.new", 11, create_missing=True, replace_path=False)

    data.set("a.new", 11, create_missing=True, replace_path=True)
    assert data.get("a.new") == 11

    # 'c.c3' is not a mapping. Even with create_missing, it will not change the structure
    with pytest.raises(ConfigException):
        data.set("c.c3.a", 11, create_missing=True, replace_path=False)

    data.set("c.c3.a", 11, create_missing=True, replace_path=True)
    assert data.get("c.c3.a") == 11

    data.set("x.a[0]", 22, create_missing=True)
    assert data.get("x.a[0]") == 22

    # This won't work: {x: a: {0: ..}}  0 is not subscriptable
    with pytest.raises(ConfigException):
        data.set("x.a[0].b", 22, create_missing=True)

    def missing_1(_data: Mapping | Sequence, key: str | int, _):
        if key == "a":
            return [None] * 1

        return {}

    assert data.set("y.a[0]", 12, create_missing=missing_1) is None
    assert data.get("y.a[0]") == 12

    assert (
        data.set("w.a[0]", 13, create_missing={"a": [None] * 1}) is None
    )
    assert data.get("w.a[0]") == 13

    # My preference and most easiest way
    assert data.set("v.a[0].b", 14, create_missing={"a": [{}]}) is None
    assert data.get("v.a[0].b") == 14

    with pytest.raises(ConfigException):
        data.set("v.a[0].b", 99, replace_value=False)

    assert data.set("v.a[0].b", 99, replace_value=True) == 14
    assert data.get("v.a[0].b") == 99


def test_delete():
    data = DeepDict(deepcopy(DATA))
    assert data.delete("a") == "aa"
    assert data.delete("does-not-exist", exception=False) is None

    with pytest.raises(ConfigException):
        data.delete("does-not-exist", exception=True)

    assert data.delete("c.c3[4].c32") == "c322"

    assert isinstance(data.delete("c.c3[4]"), Mapping)
    assert len(data.get("c.c3")) == 4

    assert isinstance(data.delete("c.c3"), List)
    assert data.get("c.c3", None) is None

    assert data.delete("c")
    assert data.get("b") == "bb"
    assert data.get("c", None) is None


def test_deep_update():
    data = DeepDict(deepcopy(DATA))
    assert data.deep_update({"a":"AA"}).get("a") == "AA"
    assert data.deep_update({"b":{"b1": "BB"}}).get("b.b1") == "BB"
    assert data.deep_update({"b":{"b1": "BB"}}).get("b.b1") == "BB"
    assert data.deep_update({"c": {"c2": {"c22": "C_222"}}}).get("c.c2.c22") == "C_222"
    assert data.deep_update({"z": "new"})["z"] == "new"
    assert data.deep_update({"b": {"b1": {"b2": "B222B"}}}).get("b.b1") == {"b2": "B222B"}
    assert data.deep_update({"b": {"b1": [1, 2, 3, 4]}}).get("b.b1") == [1, 2, 3, 4]

    # The only search pattern supported
    assert data.deep_update({"c": {"c3[*]": {"c32": "C_333"}}}).get("c..c32") == "C_333"
