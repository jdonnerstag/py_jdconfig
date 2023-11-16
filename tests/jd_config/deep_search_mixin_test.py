#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging

import pytest

from jd_config import DeepSearchMixin
from jd_config.base_model import BaseModel

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class MyClass(DeepSearchMixin, BaseModel):
    pass


def test_simple():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    data = MyClass(cfg)
    assert data.get("a") == "aa"
    assert data.get("b") == {"ba": 11, "bb": {"bba": 22, "bbb": 33}}
    assert data.get("b.ba") == 11
    assert data.get("c[3].c4b") == 55

    with pytest.raises(KeyError):
        data.get("xxx")


def test_deep():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    data = MyClass(cfg)
    assert data.get("**.a") == "aa"
    assert data.get("**.bbb") == 33
    assert data.get("b.**.bbb") == 33
    assert data.get("b.**.bb.**.bbb") == 33
    assert data.get("c.**.c4b") == 55

    with pytest.raises(KeyError):
        data.get("b.**.xxx")

    assert data.get("b.**.xxx", 99) == 99


def test_any_key_or_index():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    data = MyClass(cfg)
    assert data.get("b.*.bbb") == 33
    assert data.get("b.*.ba", None) is None
    assert data.get("c[*].c4b", None) == 55
    assert data.get("c.*.c4b", None) is None
    assert data.get("*.ba") == 11
    assert data.get("*.*.bbb") == 33
