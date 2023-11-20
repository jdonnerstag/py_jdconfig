#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C
# pylint: disable=protected-access

import logging
from copy import deepcopy

import pytest

from jd_config.base_model import BaseModel
from jd_config.env_overlay_mixin import EnvOverlayMixin

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class MyClass(EnvOverlayMixin, BaseModel):
    pass


DATA = dict(
    a="aa",
    b="bb",
    c=dict(
        c1="c11",
        c2=dict(c22="c222", c23=23, c24=24.24, c25=23_000, c26=True, C28=False),
        c3=[11, 22, 33, "4a", dict(c32="c322")],
    ),
)


def test_no_env_data():
    data = MyClass({}, env=None, env_data=None)
    with pytest.raises(KeyError):
        data.get("a")

    data = MyClass(deepcopy(DATA))
    assert data.get("a") == "aa"
    assert data.get("c.c1") == "c11"
    assert data.get("c.c2.c23") == 23
    assert data.get("c.c3[1]") == 22
    assert data.get("c.c3[4].c32") == "c322"

    assert data.get("c.xxx", "abc") == "abc"
    assert data.get("c.c3[99].a", 123) == 123

    with pytest.raises(KeyError):
        data.get("c.xxx")


def test_empty_env_data():
    data = MyClass({}, env="dev", env_data=BaseModel({}))
    with pytest.raises(KeyError):
        data.get("a")

    data = MyClass(deepcopy(DATA), env="dev", env_data=BaseModel({}))
    assert data.get("a") == "aa"
    assert data.get("c.c1") == "c11"
    assert data.get("c.c2.c23") == 23
    assert data.get("c.c3[1]") == 22
    assert data.get("c.c3[4].c32") == "c322"

    assert data.get("c.xxx", "abc") == "abc"
    assert data.get("c.c3[99].a", 123) == 123

    with pytest.raises(KeyError):
        data.get("c.xxx")


def test_simple_env_data():
    data = MyClass(
        deepcopy(DATA),
        env="dev",
        env_data=BaseModel({"a": "AA", "z": {"zz": "ZZ"}}),
    )

    assert data.get("a") == "AA"  # vs "aa"
    assert data.get("z.zz") == "ZZ"

    assert data.get("c.c1") == "c11"
    assert data.get("c.c2.c23") == 23
    assert data.get("c.c3[1]") == 22
    assert data.get("c.c3[4].c32") == "c322"

    assert data.get("c.xxx", "abc") == "abc"
    assert data.get("c.c3[99].a", 123) == 123

    with pytest.raises(KeyError):
        data.get("c.xxx")
