#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
import os
import re

from jd_config import DeepExportMixin, ResolverMixin
from jd_config.base_model import BaseModel

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args):
    return os.path.join(os.path.dirname(__file__), "data", *args)


class MyClass(DeepExportMixin, ResolverMixin, BaseModel):
    pass


def test_to_dict_to_yaml():
    cfg = {
        "a": "aa",
        "b": {
            "b1": {
                "c1": "1cc",
                "c2": "{ref:a}",
            },
            "b2": 22,
        },
        "c": ["x", "y", {"z1": "zz", "z2": "2zz"}],
        "d": "{ref:b.b1}",
    }

    data = MyClass(cfg)
    data.skip_resolver = True
    assert data["a"] == "aa"
    assert data["b"]["b1"]["c1"] == "1cc"
    assert data["b"]["b1"]["c2"] == "{ref:a}"
    assert data["b"]["b2"] == 22
    assert data["c"][0] == "x"
    assert data["c"][1] == "y"
    assert data["c"][2]["z1"] == "zz"
    assert data["c"][2]["z2"] == "2zz"
    assert data["d"] == "{ref:b.b1}"

    data.skip_resolver = False
    obj = data.to_dict()
    assert obj["b"]["b1"]["c2"] == "aa"
    assert obj["d"]["c1"] == "1cc"
    assert obj["d"]["c2"] == "aa"

    obj = data.to_dict("b.b1")
    assert obj["c1"] == "1cc"
    assert obj["c2"] == "aa"

    obj = data.to_dict("d")
    assert obj["c1"] == "1cc"
    assert obj["c2"] == "aa"

    obj = data.to_yaml("b.b1")
    obj = re.sub(r"[\r\n]+", r"\n", obj)
    assert obj == "c1: 1cc\nc2: aa\n"


def test_lazy_resolve():
    cfg = {
        "a": "aa",
        "b": {
            "b1": {
                "c1": "1cc",
                "c2": "{ref:a}",
            },
            "b2": 22,
        },
        "c": ["x", "y", {"z1": "zz", "z2": "2zz"}],
    }

    data = MyClass(cfg)
    data.skip_resolver = True
    obj = data.to_dict()
    assert obj["b"]["b1"]["c2"] == "{ref:a}"

    data.skip_resolver = False
    obj = data.to_dict()
    assert data["b"]["b1"]["c2"] == "aa"
