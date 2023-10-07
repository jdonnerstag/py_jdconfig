#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from dataclasses import dataclass
from typing import Mapping
import pytest
import logging
from jd_config import PlaceholderException, ConfigException
from jd_config import DeepGetterWithResolve, Placeholder

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_no_placeholders():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = DeepGetterWithResolve(data=cfg, path=())
    assert getter.get_path("a") == ("a",)
    assert getter.get_path("b") == ("b",)
    assert getter.get_path("b.ba") == ("b", "ba")
    assert getter.get_path("c[3].c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path("xxx")

    assert getter.get("a") == "aa"
    assert getter.get("b")
    assert getter.get("b.ba") == 11
    assert getter.get("c[3].c4b") == 55

    with pytest.raises(ConfigException):
        getter.get("xxx")

    assert getter.get("xxx", 99) == 99


def test_resolve():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": "{ref:b}",
        "d": "{ref:xxx}",
    }

    getter = DeepGetterWithResolve(data=cfg, path=())

    assert getter.get("a") == "aa"
    assert getter.get("b") == "aa"
    assert getter.get("c") == "aa"

    with pytest.raises(PlaceholderException):
        assert getter.get("d")

    with pytest.raises(ConfigException):
        assert getter.get("xxx")


def test_global_ref():
    cfg = {
        "a": "aa",
        "b": "{global:a}",
        "c": "{global:b}",
        "d": "{global:xxx}",
    }

    getter = DeepGetterWithResolve(data=cfg, path=())
    assert getter.get("a") == "aa"
    assert getter.get("b") == "aa"
    assert getter.get("c") == "aa"

    with pytest.raises(ConfigException):
        assert getter.get("d")

    with pytest.raises(ConfigException):
        assert getter.get("xxx")


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

    getter = DeepGetterWithResolve(data=cfg, path=())
    getter.register_placeholder_handler("bespoke", MyBespokePlaceholder)
    assert getter.get("a") == "it's me"


def test_mandatory_value():
    cfg = {
        "a": "???",
        "b": "{ref:a}",
    }

    getter = DeepGetterWithResolve(data=cfg, path=())
    with pytest.raises(ConfigException):
        assert getter.get("a")

    getter = DeepGetterWithResolve(data=cfg, path=())
    with pytest.raises(ConfigException):
        assert getter.get("b")


def test_detect_recursion():
    cfg = {
        "a": "{ref:b}",
        "b": "{ref:c}",
        "c": "{ref:a}",
    }

    getter = DeepGetterWithResolve(data=cfg, path=())
    with pytest.raises(ConfigException):
        getter.get("a")


def test_resolve_2():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": {"ca": "{ref:d}", "cb": [1, 2, 3, {"cb4": "{ref:d.da}"}]},
        "d": {"da": "{ref:a}"},
    }

    getter = DeepGetterWithResolve(data=cfg, path=())
    assert isinstance(getter.get("c"), Mapping)
    assert getter.get("a") == "aa"
    assert getter.get("b") == "aa"
    assert getter.get("c.ca") == {"da": "{ref:a}"}
    assert getter.get("c.cb[0]") == 1
    assert getter.get("c.cb[3].cb4") == "aa"
    assert getter.get("c.ca.da") == "aa"


def test_deep_getter_1():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = DeepGetterWithResolve(data=cfg, path=())
    assert getter.get_path("a") == ("a",)
    assert getter.get_path("b") == ("b",)
    assert getter.get_path("b.ba") == ("b", "ba")
    assert getter.get_path("c[3].c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path("xxx")

    assert getter.get("a") == "aa"
    assert getter.get("b")
    assert getter.get("b.ba") == 11
    assert getter.get("c[3].c4b") == 55

    with pytest.raises(ConfigException):
        getter.get("xxx")

    assert getter.get("xxx", 99) == 99


def test__deep_getter_2():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = DeepGetterWithResolve(data=cfg, path=())
    assert getter.get_path("..a") == ("a",)
    assert getter.get_path("..bbb") == ("b", "bb", "bbb")
    assert getter.get_path("b..bbb") == ("b", "bb", "bbb")
    assert getter.get_path("b..bb..bbb") == ("b", "bb", "bbb")
    assert getter.get_path("c..c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path("b..xxx")

    assert getter.get("..a") == "aa"
    assert getter.get("..bbb") == 33
    assert getter.get("b..bbb") == 33
    assert getter.get("b..bb..bbb") == 33
    assert getter.get("c..c4b") == 55

    with pytest.raises(ConfigException):
        getter.get("b..xxx")

    assert getter.get("b..xxx", 99) == 99


def test__deep_getter_3():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = DeepGetterWithResolve(data=cfg, path=())
    assert getter.get("b.*.bbb") == 33
    assert getter.get("b.*.ba", None) is None
    assert getter.get("c[*].c4b", None) == 55
    assert getter.get("c.*.c4b", None) is None
