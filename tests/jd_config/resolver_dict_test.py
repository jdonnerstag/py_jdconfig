#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import pytest
import logging
from typing import Mapping
from jd_config import ResolverDictList, ObjectWalker, DeepGetterWithSearch

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_dict():
    data = ResolverDictList(obj={}, path=[], root=None)
    assert len(data) == 0

    data = ResolverDictList(obj={"a": "aa"}, path=[], root=None)
    assert len(data) == 1
    assert data["a"] == "aa"
    data["a"] = "2a"
    assert data["a"] == "2a"
    assert "a" in data

    rtn = list(x for x in data.items())
    assert len(rtn) == 1
    assert rtn.pop() == ("a", "2a")

    data["b"] = "{ref:a}"
    assert len(data) == 2
    assert data["b"] == "2a"


def test_list():
    data = ResolverDictList([], path=[], root=None)
    assert len(data) == 0

    data = ResolverDictList([1, 2, 3], path=[], root=None)
    assert len(data) == 3
    assert data[1] == 2
    data[0] = 10
    assert data[0] == 10
    assert 2 in data

    rtn = list(x for x in data.items())
    assert len(rtn) == 3
    assert rtn.pop() == (2, 3)
    assert rtn.pop() == (1, 2)
    assert rtn.pop() == (0, 10)


def test_resolve():
    data = ResolverDictList(
        obj={
            "a": "aa",
            "b": "{ref:a}",
            "c": {"ca": "{ref:d}", "cb": [1, 2, 3, {"cb4": "{ref:d.da}"}]},
            "d": {"da": "{ref:a}"},
        },
        path=[],
        root=None,
    )

    assert isinstance(data["c"], Mapping)
    assert data["a"] == "aa"
    assert data["b"] == "aa"
    # It does not resolve deep. Only string values.
    assert data["c"]["ca"] == {"da": "{ref:a}"}
    assert data["c"]["cb"][0] == 1
    assert data["c"]["cb"][3]["cb4"] == "aa"
    assert data["c"]["ca"]["da"] == "aa"


def test_path():
    data = ResolverDictList(
        obj={
            "a": "aa",
            "b": "{ref:a}",
            "c": {"ca": "{ref:d}", "cb": [1, 2, 3, {"cb4": "{ref:d.da}"}]},
            "d": {"da": "{ref:a}"},
        },
        path=[],
        root=None,
    )

    assert data.path == []
    assert data["c"].path == ["c"]
    assert data["c"]["ca"].path == ["c", "ca"]
    assert data["c"]["cb"].path == ["c", "cb"]
    assert data["c"]["cb"][3].path == ["c", "cb", 3]


def test_objwalk():
    data = ResolverDictList(
        obj={
            "a": "aa",
            "b": "{ref:a}",
            "c": {"ca": "{ref:d}", "cb": [1, 2, 3, {"cb4": "{ref:d.da}"}]},
            "d": {"da": "{ref:a}"},
        },
        path=[],
        root=None,
    )

    data = list(x.path for x in ObjectWalker.objwalk(data, nodes_only=True))
    data.remove(("a",))
    data.remove(("b",))
    data.remove(("c", "ca", "da"))
    data.remove(("c", "cb", 0))
    data.remove(("c", "cb", 1))
    data.remove(("c", "cb", 2))
    data.remove(("c", "cb", 3, "cb4"))
    data.remove(("d", "da"))

    assert len(data) == 0


def test_objwalk_with_references():
    data = ResolverDictList(
        obj=dict(
            a="aa",
            b="{ref:a}",
            c=dict(
                c1="{ref:c.c3[4]}",
                c2=dict(c22="c222", c23=23, c24=24.24, c25=23_000, c26=True, c27=False),
                c3=[11, 22, 33, "4a", dict(c32="{ref:b}")],
            ),
        ),
        path=[],
        root=None,
    )

    x = 0
    data = list(x.path for x in ObjectWalker.objwalk(data, nodes_only=True))
    data.remove(("a",))
    data.remove(("b",))
    data.remove(("c", "c1", "c32"))
    data.remove(("c", "c2", "c22"))
    data.remove(("c", "c2", "c23"))
    data.remove(("c", "c2", "c24"))
    data.remove(("c", "c2", "c25"))
    data.remove(("c", "c2", "c26"))
    data.remove(("c", "c2", "c27"))

    data.remove(("c", "c3", 0))  # List elements are integer (not string)
    data.remove(("c", "c3", 1))  # List element
    data.remove(("c", "c3", 2))  # List element
    data.remove(("c", "c3", 3))  # List element
    data.remove(("c", "c3", 4, "c32"))

    assert len(data) == 0


def test_deep_getter_1():
    cfg = ResolverDictList(
        obj={
            "a": "aa",
            "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
            "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
        },
        path=[],
        root=None,
    )

    getter = DeepGetterWithSearch()
    assert getter.get_path(cfg, "a") == ["a"]
    assert getter.get_path(cfg, "b") == ["b"]
    assert getter.get_path(cfg, "b.ba") == ["b", "ba"]
    assert getter.get_path(cfg, "c[3].c4b") == ["c", 3, "c4b"]

    with pytest.raises(KeyError):
        getter.get_path(cfg, "xxx")

    assert getter.get(cfg, "a") == "aa"
    assert getter.get(cfg, "b")
    assert getter.get(cfg, "b.ba") == 11
    assert getter.get(cfg, "c[3].c4b") == 55

    with pytest.raises(KeyError):
        getter.get(cfg, "xxx")

    assert getter.get(cfg, "xxx", 99) == 99


def test__deep_getter_2():
    cfg = ResolverDictList(
        obj={
            "a": "aa",
            "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
            "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
        },
        path=[],
        root=None,
    )

    getter = DeepGetterWithSearch()
    assert getter.get_path(cfg, "..a") == ["a"]
    assert getter.get_path(cfg, "..bbb") == ["b", "bb", "bbb"]
    assert getter.get_path(cfg, "b..bbb") == ["b", "bb", "bbb"]
    assert getter.get_path(cfg, "b..bb..bbb") == ["b", "bb", "bbb"]
    assert getter.get_path(cfg, "c..c4b") == ["c", 3, "c4b"]

    with pytest.raises(KeyError):
        getter.get_path(cfg, "b..xxx")

    assert getter.get(cfg, "..a") == "aa"
    assert getter.get(cfg, "..bbb") == 33
    assert getter.get(cfg, "b..bbb") == 33
    assert getter.get(cfg, "b..bb..bbb") == 33
    assert getter.get(cfg, "c..c4b") == 55

    with pytest.raises(KeyError):
        getter.get(cfg, "b..xxx")

    assert getter.get(cfg, "b..xxx", 99) == 99


def test__deep_getter_3():
    cfg = ResolverDictList(
        obj={
            "a": "aa",
            "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
            "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
        },
        path=[],
        root=None,
    )

    getter = DeepGetterWithSearch()
    assert getter.get(cfg, "b.*.bbb") == 33
    assert getter.get(cfg, "b.*.ba", None) is None
    assert getter.get(cfg, "c[*].c4b", None) == 55
    assert getter.get(cfg, "c.*.c4b", None) is None
