#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from typing import Any

import pytest

from jd_config import ConfigException, DeepGetter

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_auto_created_context():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = DeepGetter()
    assert getter.get_path(cfg, "a") == ("a",)
    assert getter.get_path(cfg, "b") == ("b",)
    assert getter.get_path(cfg, "b.ba") == ("b", "ba")
    assert getter.get_path(cfg, "c[3].c4b") == ("c", 3, "c4b")

    with pytest.raises(ConfigException):
        getter.get_path(cfg, "xxx")  # path does not exist

    assert getter.get(cfg, "a") == "aa"
    assert getter.get(cfg, "b")
    assert getter.get(cfg, "b.ba") == 11
    assert getter.get(cfg, "c[3].c4b") == 55

    with pytest.raises(ConfigException):
        getter.get(cfg, "xxx")

    assert getter.get(cfg, "xxx", 99) == 99


def test_manual_context():
    cfg = {
        "a": "aa",
        "b": {"ba": 11, "bb": {"bba": 22, "bbb": 33}},
        "c": [1, 2, 3, {"c4a": 44, "c4b": 55}],
    }

    getter = DeepGetter()
    assert getter.get(cfg, "a") == "aa"
    assert getter.get(cfg, "b")
    assert getter.get(cfg, "b.ba") == 11
    assert getter.get(cfg, "c[3].c4b") == 55

    with pytest.raises(ConfigException):
        getter.get(cfg, "xxx")

    def on_missing(*_) -> Any:
        return "not found"

    getter.on_missing = on_missing
    assert getter.get(cfg, "xxx") == "not found"

    getter = DeepGetter(on_missing=on_missing)
    assert getter.get(cfg, "xxx") == "not found"
