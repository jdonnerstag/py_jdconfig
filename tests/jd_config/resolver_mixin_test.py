#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from dataclasses import dataclass

import pytest

from jd_config import Placeholder, ResolverMixin
from jd_config.base_model import BaseModel
from jd_config.deep_search_mixin import DeepSearchMixin
from jd_config.placeholders import PlaceholderException
from jd_config.utils import ConfigException

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class MyClass(DeepSearchMixin, ResolverMixin, BaseModel):
    pass


def test_no_placeholders():
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

    assert data.get("xxx", 99) == 99


def test_resolve():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": "{ref:b}",
        "d": "{ref:xxx}",
    }

    data = MyClass(cfg)
    assert data.get("a") == "aa"
    assert data.get("b") == "aa"
    assert data.get("c") == "aa"

    with pytest.raises(
        PlaceholderException
    ):  # TODO Make it KeyError, or derive from KeyError
        assert data.get("d")

    with pytest.raises(KeyError):
        assert data.get("xxx")


def test_global_ref():
    cfg = {
        "a": "aa",
        "b": "{global:a}",
        "c": "{global:b}",
        "d": "{global:xxx}",
    }

    data = MyClass(cfg)
    assert data.get("a") == "aa"
    assert data.get("b") == "aa"
    assert data.get("c") == "aa"

    with pytest.raises(PlaceholderException):
        assert data.get("d")

    with pytest.raises(KeyError):
        assert data.get("xxx")


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

    data = MyClass(cfg)
    data.register_placeholder_handler("bespoke", MyBespokePlaceholder)

    assert data.get("a") == "it's me"


def test_mandatory_value():
    cfg = {
        "a": "???",
        "b": "{ref:a}",
    }

    data = MyClass(cfg)
    with pytest.raises(ConfigException):  # TODO make it a subclass of KeyError
        assert data.get("a")

    with pytest.raises(ConfigException):
        assert data.get("b")


def test_detect_recursion():
    cfg = {
        "a": "{ref:b}",
        "b": "{ref:c}",
        "c": "{ref:a}",
    }

    data = MyClass(cfg)
    with pytest.raises(ConfigException):  # TODO Make it KeyError
        data.get("a")


def test_resolve_2():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": {"ca": "{ref:d}", "cb": [1, 2, 3, {"cb4": "{ref:d.da}"}]},
        "d": {"da": "{ref:a}"},
    }

    data = MyClass(cfg)
    assert data.get("a") == "aa"
    assert data.get("b") == "aa"
    assert data.get("c.ca") == {"da": "{ref:a}"}
    assert data.get("c.cb[0]") == 1
    assert data.get("c.cb[3].cb4") == "aa"
    assert data.get("c.ca.da") == "aa"


def test_deep_data_1():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    data = MyClass(cfg)
    assert data.get("a") == "aa"
    assert data.get("b")
    assert data.get("b.ba") == 11
    assert data.get("c[3].c4b") == 55

    with pytest.raises(KeyError):
        data.get("xxx")

    assert data.get("xxx", 99) == 99


def test_deep_data_2():
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


def test_deep_data_3():
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
