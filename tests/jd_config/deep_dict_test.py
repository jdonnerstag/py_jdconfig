#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C
# pylint: disable=protected-access

from dataclasses import dataclass
import logging
from copy import deepcopy
from typing import List, Mapping

import pytest

from jd_config import ConfigException, DeepDict
from jd_config.deep_getter import GetterContext
from jd_config.placeholders import Placeholder

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
    data = DeepDict({})
    with pytest.raises(ConfigException):
        data.get("a")

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

    # 'a' exists, but is no container. Even with create_missing, it will not change the structure
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

    def missing_1(ctx: GetterContext, _exc):
        if ctx.key == "a":
            return [None] * 1

        return {}

    assert data.set("y.a[0]", 12, create_missing=missing_1) is None

    # Note that missing_1() is not updating the config; which is perfectly
    # fine. But a subsequent call w/o create_missing will fail, because
    # it can not find the elem.
    with pytest.raises(ConfigException):
        data.get("y.a[0]")

    # My preference and most easiest way: provide a dict with the
    # non-Mapping keys only.
    assert data.set("w.a[0]", 13, create_missing={"a": [None] * 1}) is None
    assert data.get("w.a[0]") == 13

    assert data.set("v.a[0].b", 14, create_missing={"a": [{}]}) is None
    assert data.get("v.a[0].b") == 14

    assert (
        data.set("b.b1", {"bb1": "B"}, create_missing=True, replace_path=True) is None
    )
    assert data.get("b.b1") == {"bb1": "B"}
    assert (
        data.set("b.b1", [1, 2, 3, 4], create_missing=True, replace_path=True)
        is not None
    )
    assert data.get("b.b1") == [1, 2, 3, 4]


def test_delete():
    data = DeepDict(deepcopy(DATA))
    assert data.delete("a") == "aa"
    assert data.delete("does-not-exist", exception=False) is None

    with pytest.raises(KeyError):
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
    assert data.deep_update({"a": "AA"}).get("a") == "AA"
    assert data.deep_update({"b": {"b1": "BB"}}).get("b.b1") == "BB"
    assert data.deep_update({"b": {"b1": "BB"}}).get("b.b1") == "BB"
    assert data.deep_update({"c": {"c2": {"c22": "C_222"}}}).get("c.c2.c22") == "C_222"
    assert data.deep_update({"z": "new"})["z"] == "new"
    assert data.deep_update({"b": {"b1": {"b2": "B222B"}}}).get("b.b1") == {
        "b2": "B222B"
    }

    # This one is tricky
    assert data.deep_update({"b": {"b1": [1, 2, 3, 4]}}).get("b.b1") == [1, 2, 3, 4]


def test_lazy_resolve():
    data = DeepDict(deepcopy(DATA))
    data["c"]["c2"]["c22"] = "{ref:a}"
    assert data["c"]["c2"]["c22"] == "aa"  # pylint: disable=unsubscriptable-object
    assert data.get("c.c2.c22", resolve=True) == "aa"
    assert data.get("c.c2.c22", resolve=False) == "{ref:a}"


@dataclass
class MyBespokePlaceholder(Placeholder):
    # This is also a test for a placeholder that does not take any parameters

    def resolve(self, *_, **__):
        return "it's me"


def test_bespoke_placeholder():
    cfg = {
        "a": "{ref:b}",
        "b": "{bespoke:}",
    }

    data = DeepDict(cfg)
    data.register_placeholder_handler("bespoke", MyBespokePlaceholder)
    assert data.get("a") == "it's me"
