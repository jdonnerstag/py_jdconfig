#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from jd_config import DictList

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_dict():
    data = DictList({})
    assert len(data) == 0

    data = DictList({"a": "aa"})
    assert len(data) == 1
    assert data["a"] == "aa"
    data["a"] = "2a"
    assert data["a"] == "2a"
    assert "a" in data

    rtn = list(x for x in data.items())
    assert len(rtn) == 1
    assert rtn.pop() == ("a", "2a")

    rtn = list(x for x in data.keys())
    assert len(rtn) == 1
    assert rtn.pop() == "a"

    rtn = list(x for x in data.values())
    assert len(rtn) == 1
    assert rtn.pop() == "2a"

def test_list():
    data = DictList([])
    assert len(data) == 0

    data = DictList([1, 2, 3])
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

    rtn = list(x for x in data.keys())
    assert len(rtn) == 3
    assert rtn.pop() == 2
    assert rtn.pop() == 1
    assert rtn.pop() == 0

    rtn = list(x for x in data.values())
    assert len(rtn) == 3
    assert rtn.pop() == 3
    assert rtn.pop() == 2
    assert rtn.pop() == 10
