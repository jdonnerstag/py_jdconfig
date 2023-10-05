#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from typing import Mapping
from jd_config import ResolverDictList

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_dict():
    data = ResolverDictList(obj={}, path=[])
    assert len(data) == 0

    data = ResolverDictList(obj={"a": "aa"}, path=[])
    assert len(data) == 1
    assert data["a"] == "aa"
    data["a"] = "2a"
    assert data["a"] == "2a"
    assert "a" in data

    rtn = list(x for x in data)
    assert len(rtn) == 1
    assert rtn.pop() == ("a", "2a")

    data["b"] = "{ref:a}"
    assert len(data) == 2
    assert data["b"] == "{ref:a}"

def test_list():
    data = ResolverDictList([], path=[])
    assert len(data) == 0

    data = ResolverDictList([1, 2, 3], path=[])
    assert len(data) == 3
    assert data[1] == 2
    data[0] = 10
    assert data[0] == 10
    assert 2 in data

    rtn = list(x for x in data)
    assert len(rtn) == 3
    assert rtn.pop() == (2, 3)
    assert rtn.pop() == (1, 2)
    assert rtn.pop() == (0, 10)

def test_resolve():

    data = ResolverDictList(obj={
        "a": "aa",
        "b": "{ref:a}",
        "c": {
            "ca": "{ref:d}",
            "cb": [1, 2, 3, {"cb4": "{ref:d.da}"}]
        },
        "d": {"da": "{ref:a}"}
    }, path=[])

    assert isinstance(data["c"], Mapping)
    assert data["c"]["ca"] == "{ref:d}"
    assert data["c"]["cb"][0] == 1
    assert data["c"]["cb"][3]["cb4"] == "{ref:d.da}"

    assert data.resolve("a", data) == "aa"
    assert data.resolve("b", data) == "aa"
    assert data.resolve("c", data).resolve("ca", data) == {"da": "{ref:a}"}
    assert data.resolve("c", data).resolve("cb", data).resolve(0, data) == 1
    assert data.resolve("c", data).resolve("cb", data).resolve(3, data).resolve("cb4", data) == "aa"
    assert data.resolve("c", data).resolve("ca", data).resolve("da", data) == "aa"

