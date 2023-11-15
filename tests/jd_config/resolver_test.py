#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from dataclasses import dataclass
from typing import Mapping

import pytest

from jd_config import (
    ConfigException,
    DeepGetter,
    DeepSearch,
    GetterContext,
    Placeholder,
    Resolver,
)
from jd_config.config_path_extended import ExtendedCfgPath

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def new_getter():
    getter = DeepGetter()
    resolver = Resolver()
    getter.getter_pipeline = (
        DeepSearch.cb_get,
        resolver.cb_get,
    ) + getter.getter_pipeline

    return getter


def test_no_placeholders():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = new_getter()
    assert getter.get_path(GetterContext(cfg), "a") == ("a",)
    assert getter.get_path(GetterContext(cfg), "b") == ("b",)
    assert getter.get_path(GetterContext(cfg), "b.ba") == ("b", "ba")
    assert getter.get_path(GetterContext(cfg), "c[3].c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path(GetterContext(cfg), "xxx")

    assert getter.get(GetterContext(cfg), "a") == "aa"
    assert getter.get(GetterContext(cfg), "b")
    assert getter.get(GetterContext(cfg), "b.ba") == 11
    assert getter.get(GetterContext(cfg), "c[3].c4b") == 55

    with pytest.raises(ConfigException):
        getter.get(GetterContext(cfg), "xxx")

    assert getter.get(GetterContext(cfg), "xxx", 99) == 99


def test_resolve():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": "{ref:b}",
        "d": "{ref:xxx}",
    }

    getter = new_getter()
    assert getter.get(GetterContext(cfg), "a") == "aa"
    assert getter.get(GetterContext(cfg), "b") == "aa"
    assert getter.get(GetterContext(cfg), "c") == "aa"

    with pytest.raises(ConfigException):
        assert getter.get(GetterContext(cfg), "d")

    with pytest.raises(ConfigException):
        assert getter.get(GetterContext(cfg), "xxx")


def test_global_ref():
    cfg = {
        "a": "aa",
        "b": "{global:a}",
        "c": "{global:b}",
        "d": "{global:xxx}",
    }

    getter = new_getter()
    assert getter.get(GetterContext(cfg), "a") == "aa"
    assert getter.get(GetterContext(cfg), "b") == "aa"
    assert getter.get(GetterContext(cfg), "c") == "aa"

    with pytest.raises(ConfigException):
        assert getter.get(GetterContext(cfg), "d")

    with pytest.raises(ConfigException):
        assert getter.get(GetterContext(cfg), "xxx")


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

    getter = DeepGetter()
    resolver = Resolver()
    resolver.register_placeholder_handler("bespoke", MyBespokePlaceholder)
    getter.getter_pipeline = (
        DeepSearch.cb_get,
        resolver.cb_get,
    ) + getter.getter_pipeline

    assert getter.get(GetterContext(cfg), "a") == "it's me"


def test_mandatory_value():
    cfg = {
        "a": "???",
        "b": "{ref:a}",
    }

    getter = new_getter()
    with pytest.raises(ConfigException):
        assert getter.get(GetterContext(cfg), "a")

    with pytest.raises(ConfigException):
        assert getter.get(GetterContext(cfg), "b")


def test_detect_recursion():
    cfg = {
        "a": "{ref:b}",
        "b": "{ref:c}",
        "c": "{ref:a}",
    }

    getter = new_getter()
    with pytest.raises(ConfigException):
        getter.get(GetterContext(cfg), "a")


def test_resolve_2():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": {"ca": "{ref:d}", "cb": [1, 2, 3, {"cb4": "{ref:d.da}"}]},
        "d": {"da": "{ref:a}"},
    }

    getter = new_getter()
    assert isinstance(getter.get(GetterContext(cfg), "c"), Mapping)
    assert getter.get(GetterContext(cfg), "a") == "aa"
    assert getter.get(GetterContext(cfg), "b") == "aa"
    assert getter.get(GetterContext(cfg), "c.ca") == {"da": "{ref:a}"}
    assert getter.get(GetterContext(cfg), "c.cb[0]") == 1
    assert getter.get(GetterContext(cfg), "c.cb[3].cb4") == "aa"
    assert getter.get(GetterContext(cfg), "c.ca.da") == "aa"


def test_deep_getter_1():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = new_getter()
    assert getter.get_path(GetterContext(cfg), "a") == ("a",)
    assert getter.get_path(GetterContext(cfg), "b") == ("b",)
    assert getter.get_path(GetterContext(cfg), "b.ba") == ("b", "ba")
    assert getter.get_path(GetterContext(cfg), "c[3].c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path(GetterContext(cfg), "xxx")

    assert getter.get(GetterContext(cfg), "a") == "aa"
    assert getter.get(GetterContext(cfg), "b")
    assert getter.get(GetterContext(cfg), "b.ba") == 11
    assert getter.get(GetterContext(cfg), "c[3].c4b") == 55

    with pytest.raises(ConfigException):
        getter.get(GetterContext(cfg), "xxx")

    assert getter.get(GetterContext(cfg), "xxx", 99) == 99


def test_deep_getter_2():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = new_getter()
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


def test_deep_getter_3():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = new_getter()
    getter.cfg_path_type = ExtendedCfgPath
    assert getter.get(GetterContext(cfg), "b.*.bbb") == 33
    assert getter.get(GetterContext(cfg), "b.*.ba", None) is None
    assert getter.get(GetterContext(cfg), "c[*].c4b", None) == 55
    assert getter.get(GetterContext(cfg), "c.*.c4b", None) is None
