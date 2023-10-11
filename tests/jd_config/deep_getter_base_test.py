#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import pytest
import logging
from jd_config import ConfigException
from jd_config.deep_getter_base import DeepGetter

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_simple():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = DeepGetter(data=cfg, path=())
    assert getter.get_path("a") == ("a",)
    assert getter.get_path("b") == ("b",)
    assert getter.get_path("b.ba") == ("b", "ba")
    assert getter.get_path("c[3].c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path("xxx") # path does not exist

    assert getter.get("a") == "aa"
    assert getter.get("b")
    assert getter.get("b.ba") == 11
    assert getter.get("c[3].c4b") == 55

    with pytest.raises(ConfigException):
        getter.get("xxx")

    assert getter.get("xxx", 99) == 99


def test_resolve_only():
    """
    Imagine `{import: ./db/{ref:db}/config.yaml}` where {import:..} should load
    a file, but the filename `./db/{ref:db}/config.yaml` itself is a combination
    of text and reference placeholder. Obviously we want to re-use the same
    source code (resolver), which is doing exactly the same in other places. 


    """
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = DeepGetter(data=cfg, path=())
    assert getter.get_path("a") == ("a",)
    assert getter.get_path("b") == ("b",)
    assert getter.get_path("b.ba") == ("b", "ba")
    assert getter.get_path("c[3].c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path("xxx") # path does not exist

    assert getter.get("a") == "aa"
    assert getter.get("b")
