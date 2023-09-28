#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import os
import re
import logging
from jd_config import DeepExportMixin, ResolverMixin, DeepAccessMixin

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args):
    return os.path.join(os.path.dirname(__file__), "data", *args)


class MyMixinTestClass(DeepExportMixin, ResolverMixin, DeepAccessMixin):
    def __init__(self) -> None:
        self.data = None

        ResolverMixin.__init__(self)
        DeepExportMixin.__init__(self)
        DeepAccessMixin.__init__(self)


def test_to_dict_to_yaml():
    cfg = MyMixinTestClass()

    cfg.data = {
        "a": "aa",
        "b": {
            "b1": {
                "c1": "1cc",
                "c2": "2cc",
            },
            "b2": 22,
        },
        "c": ["x", "y", {"z1": "zz", "z2": "2zz"}],
    }

    data = cfg.to_dict()
    assert data["a"] == "aa"
    assert data["b"]["b1"]["c1"] == "1cc"
    assert data["b"]["b1"]["c2"] == "2cc"
    assert data["b"]["b2"] == 22
    assert data["c"][0] == "x"
    assert data["c"][1] == "y"
    assert data["c"][2]["z1"] == "zz"
    assert data["c"][2]["z2"] == "2zz"

    data = cfg.to_yaml("b.b1")
    data = re.sub(r"[\r\n]+", r"\n", data)
    assert data == "c1: 1cc\nc2: 2cc\n"
