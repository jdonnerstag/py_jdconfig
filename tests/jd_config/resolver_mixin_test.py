#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from dataclasses import dataclass
from typing import Mapping

import pytest

from jd_config import ConfigException, Placeholder
from jd_config.deep_search_mixin import DeepSearchMixin
from jd_config.deep_getter import DeepGetter
from jd_config.resolver_mixin import ResolverMixin

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


# Note: the order of the subclasses is relevant !!!
class MyConfig(DeepSearchMixin, ResolverMixin, DeepGetter):
    def __init__(self) -> None:
        DeepGetter.__init__(self)
        ResolverMixin.__init__(self)
        DeepSearchMixin.__init__(self)


def test_no_placeholders():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = MyConfig()
    assert getter.get_path(cfg, "a") == ("a",)
    assert getter.get_path(cfg, "b") == ("b",)
    assert getter.get_path(cfg, "b.ba") == ("b", "ba")
    assert getter.get_path(cfg, "c[3].c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path(cfg, "xxx")

    assert getter.get(cfg, "a") == "aa"
    assert getter.get(cfg, "b")
    assert getter.get(cfg, "b.ba") == 11
    assert getter.get(cfg, "c[3].c4b") == 55

    with pytest.raises(ConfigException):
        getter.get(cfg, "xxx")

    assert getter.get(cfg, "xxx", 99) == 99


def test_resolve():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": "{ref:b}",
        "d": "{ref:xxx}",
    }

    getter = MyConfig()
    assert getter.get(cfg, "a") == "aa"
    assert getter.get(cfg, "b") == "aa"
    assert getter.get(cfg, "c") == "aa"

    with pytest.raises(ConfigException):
        assert getter.get(cfg, "d")

    with pytest.raises(ConfigException):
        assert getter.get(cfg, "xxx")


def test_global_ref():
    cfg = {
        "a": "aa",
        "b": "{global:a}",
        "c": "{global:b}",
        "d": "{global:xxx}",
    }

    # TODO {global:} so far is == {ref:}
    getter = MyConfig()
    assert getter.get(cfg, "a") == "aa"
    assert getter.get(cfg, "b") == "aa"
    assert getter.get(cfg, "c") == "aa"

    with pytest.raises(ConfigException):
        assert getter.get(cfg, "d")

    with pytest.raises(ConfigException):
        assert getter.get(cfg, "xxx")


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

    getter = MyConfig()
    getter.register_placeholder_handler("bespoke", MyBespokePlaceholder)
    assert getter.get(cfg, "a") == "it's me"


def test_mandatory_value():
    cfg = {
        "a": "???",
        "b": "{ref:a}",
    }

    getter = MyConfig()
    with pytest.raises(ConfigException):
        assert getter.get(cfg, "a")

    with pytest.raises(ConfigException):
        assert getter.get(cfg, "b")


def test_detect_recursion():
    cfg = {
        "a": "{ref:b}",
        "b": "{ref:c}",
        "c": "{ref:a}",
    }

    getter = MyConfig()
    with pytest.raises(RecursionError):
        getter.get(cfg, "a")


def test_resolve_2():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": {"ca": "{ref:d}", "cb": [1, 2, 3, {"cb4": "{ref:d.da}"}]},
        "d": {"da": "{ref:a}"},
    }

    getter = MyConfig()
    assert isinstance(getter.get(cfg, "c"), Mapping)
    assert getter.get(cfg, "a") == "aa"
    assert getter.get(cfg, "b") == "aa"
    assert getter.get(cfg, "c.ca") == {"da": "{ref:a}"}
    assert getter.get(cfg, "c.cb[0]") == 1
    assert getter.get(cfg, "c.cb[3].cb4") == "aa"
    assert getter.get(cfg, "c.ca.da") == "aa"


def test_deep_getter_1():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = MyConfig()
    assert getter.get_path(cfg, "a") == ("a",)
    assert getter.get_path(cfg, "b") == ("b",)
    assert getter.get_path(cfg, "b.ba") == ("b", "ba")
    assert getter.get_path(cfg, "c[3].c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path(cfg, "xxx")

    assert getter.get(cfg, "a") == "aa"
    assert getter.get(cfg, "b")
    assert getter.get(cfg, "b.ba") == 11
    assert getter.get(cfg, "c[3].c4b") == 55

    with pytest.raises(ConfigException):
        getter.get(cfg, "xxx")

    assert getter.get(cfg, "xxx", 99) == 99


def test_deep_getter_2():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = MyConfig()
    assert getter.get_path(cfg, "..a") == ("a",)
    assert getter.get_path(cfg, "..bbb") == ("b", "bb", "bbb")
    assert getter.get_path(cfg, "b..bbb") == ("b", "bb", "bbb")
    assert getter.get_path(cfg, "b..bb..bbb") == ("b", "bb", "bbb")
    assert getter.get_path(cfg, "c..c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path(cfg, "b..xxx")

    assert getter.get(cfg, "..a") == "aa"
    assert getter.get(cfg, "..bbb") == 33
    assert getter.get(cfg, "b..bbb") == 33
    assert getter.get(cfg, "b..bb..bbb") == 33
    assert getter.get(cfg, "c..c4b") == 55

    with pytest.raises(ConfigException):
        getter.get(cfg, "b..xxx")

    assert getter.get(cfg, "b..xxx", 99) == 99


def test_deep_getter_3():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = MyConfig()
    assert getter.get(cfg, "b.*.bbb") == 33
    assert getter.get(cfg, "b.*.ba", None) is None
    assert getter.get(cfg, "c[*].c4b", None) == 55
    assert getter.get(cfg, "c.*.c4b", None) is None
