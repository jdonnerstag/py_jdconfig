#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import os
import re
import logging
from jd_config import DeepExportMixin, ResolverMixin, DeepAccessMixin, RefPlaceholder, YamlObj

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

    # TODO make it able to lazy resolve, so that "c2": "{ref:a}" can be used as well
    # The test should go into config_getter?
    cfg.data = {
        "a": "aa",
        "b": {
            "b1": {
                "c1": "1cc",
                "c2": YamlObj(0, 0, None, [RefPlaceholder("a")]),
            },
            "b2": 22,
        },
        "c": ["x", "y", {"z1": "zz", "z2": "2zz"}],
    }

    data = cfg.to_dict(resolve=False)
    assert data["a"] == "aa"
    assert data["b"]["b1"]["c1"] == "1cc"
    assert data["b"]["b1"]["c2"].value == [RefPlaceholder("a")]
    assert data["b"]["b2"] == 22
    assert data["c"][0] == "x"
    assert data["c"][1] == "y"
    assert data["c"][2]["z1"] == "zz"
    assert data["c"][2]["z2"] == "2zz"

    data = cfg.to_dict(resolve=True)
    assert data["b"]["b1"]["c2"] == "aa"

    data = cfg.to_yaml("b.b1")
    data = re.sub(r"[\r\n]+", r"\n", data)
    assert data == "c1: 1cc\nc2: aa\n"

def test_lazy_resolve():
    cfg = MyMixinTestClass()
    cfg.data = {
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

    data = cfg.to_dict(resolve=False)
    assert data["b"]["b1"]["c2"] == "{ref:a}"

    data = cfg.to_dict(resolve=True)
    assert data["b"]["b1"]["c2"] == "aa"
