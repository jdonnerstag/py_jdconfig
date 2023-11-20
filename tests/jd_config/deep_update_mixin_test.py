#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from copy import deepcopy

from jd_config.base_model import BaseModel
from jd_config.deep_dict_mixin import DeepDictMixin
from jd_config.deep_update_mixin import DeepUpdateMixin

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class MyClass(DeepDictMixin, DeepUpdateMixin, BaseModel):
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


def test_deep_update():
    data = MyClass(deepcopy(DATA))
    assert data.deep_update({"a": "AA"}).get("a") == "AA"
    assert data.deep_update({"b": {"b1": "BB"}}).get("b.b1") == "BB"
    assert data.deep_update({"b": {"b1": "BB"}}).get("b.b1") == "BB"
    assert data.deep_update({"c": {"c2": {"c22": "C_222"}}}).get("c.c2.c22") == "C_222"
    assert data.deep_update({"z": "new"})["z"] == "new"
    assert data.deep_update({"b": {"b1": {"b2": "B222B"}}}).get("b.b1") == {
        "b2": "B222B"
    }

    # This one is tricky
    assert data.deep_update({"b": {"b1": [1, 2, 3, 4]}}).get("b.b1") == [1, 2, 3, 4]


def test_set_dotted():
    data = MyClass(deepcopy(DATA))
    assert data.deep_update({"b.b1": "AA"}).get("b.b1") == "AA"
    assert data.deep_update({"z.new": "zz"}).get("z.new") == "zz"
