#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from typing import Mapping, Optional
import pytest
import logging
from jd_config import ConfigException, NonStrSequence, PathType
from jd_config.deep_getter_base import DeepGetter
from jd_config.deep_getter_with_search import ConfigSearchMixin

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class MyConfig(ConfigSearchMixin, DeepGetter):
    def __init__(self, data: Mapping | NonStrSequence, path: PathType, *, _memo: list | None = None) -> None:
        DeepGetter.__init__(self, data, path, _memo=_memo)
        ConfigSearchMixin.__init__(self)


def test_simple():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = MyConfig(data=cfg, path=())
    assert getter.get_path("a") == ("a",)
    assert getter.get_path("b") == ("b",)
    assert getter.get_path("b.ba") == ("b", "ba")
    assert getter.get_path("c[3].c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path("xxx")


def test_deep():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = MyConfig(data=cfg, path=())
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


def test_any_key_or_index():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = MyConfig(data=cfg, path=())
    assert getter.get("b.*.bbb") == 33
    assert getter.get("b.*.ba", None) is None
    assert getter.get("c[*].c4b", None) == 55
    assert getter.get("c.*.c4b", None) is None
    assert getter.get("*.ba") == 11
    # assert getter.get("*.*.bbb") == 33   # TODO Not yet supported
