#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging

import pytest

from jd_config import ConfigException, DeepGetter, DeepSearchMixin, GetterContext

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class MyConfig(DeepSearchMixin, DeepGetter):
    def __init__(self) -> None:
        DeepGetter.__init__(self)
        DeepSearchMixin.__init__(self)


def test_simple():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = MyConfig()
    assert getter.get_path(GetterContext(cfg), "a") == ("a",)
    assert getter.get_path(GetterContext(cfg), "b") == ("b",)
    assert getter.get_path(GetterContext(cfg), "b.ba") == ("b", "ba")
    assert getter.get_path(GetterContext(cfg), "c[3].c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path(GetterContext(cfg), "xxx")


def test_deep():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = MyConfig()
    assert getter.get_path(GetterContext(cfg), "**.a") == ("a",)
    assert getter.get_path(GetterContext(cfg), "**.bbb") == ("b", "bb", "bbb")
    assert getter.get_path(GetterContext(cfg), "b.**.bbb") == ("b", "bb", "bbb")
    assert getter.get_path(GetterContext(cfg), "b.**.bb.**.bbb") == ("b", "bb", "bbb")
    assert getter.get_path(GetterContext(cfg), "c.**.c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path(GetterContext(cfg), "b.**.xxx")

    assert getter.get(GetterContext(cfg), "**.a") == "aa"
    assert getter.get(GetterContext(cfg), "**.bbb") == 33
    assert getter.get(GetterContext(cfg), "b.**.bbb") == 33
    assert getter.get(GetterContext(cfg), "b.**.bb.**.bbb") == 33
    assert getter.get(GetterContext(cfg), "c.**.c4b") == 55

    with pytest.raises(ConfigException):
        getter.get(GetterContext(cfg), "b.**.xxx")

    assert getter.get(GetterContext(cfg), "b.**.xxx", 99) == 99


def test_any_key_or_index():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = MyConfig()
    assert getter.get(GetterContext(cfg), "b.*.bbb") == 33
    assert getter.get(GetterContext(cfg), "b.*.ba", None) is None
    assert getter.get(GetterContext(cfg), "c[*].c4b", None) == 55
    assert getter.get(GetterContext(cfg), "c.*.c4b", None) is None
    assert getter.get(GetterContext(cfg), "*.ba") == 11
    assert getter.get(GetterContext(cfg), "*.*.bbb") == 33

    assert getter.get_path(GetterContext(cfg), "*.*.bbb") == ("b", "bb", "bbb")
