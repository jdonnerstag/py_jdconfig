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

    assert getter.get_path("xxx") == ("xxx",) # get_path() is not validate it exists

    assert getter.get("a") == "aa"
    assert getter.get("b")
    assert getter.get("b.ba") == 11
    assert getter.get("c[3].c4b") == 55

    with pytest.raises(ConfigException):
        getter.get("xxx")

    assert getter.get("xxx", 99) == 99
