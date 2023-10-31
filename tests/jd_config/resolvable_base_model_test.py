#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
import os
from pathlib import Path

import pytest
from jd_config.config_base_model import ConfigMeta
from jd_config.descriptor import ConfigDescriptor

from jd_config.resolvable_base_model import ResolvableBaseModel
from jd_config.utils import ConfigException
from jd_config.value_reader import ValueReader

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args) -> Path:
    return Path(os.path.join(os.path.dirname(__file__), "data", *args))


class A(ResolvableBaseModel):
    a: str = ConfigDescriptor()
    b: str = ConfigDescriptor()
    c: str = ConfigDescriptor()


class App:
    value_reader: ValueReader = ValueReader()


def test_simple():
    data = dict(
        a="a",
        b="{ref:a}",
        c="{ref:b}",
    )

    meta = ConfigMeta(app=App(), data=data)
    app = A(meta=meta)
    assert app
    assert app.a == "a"
    assert app.b == "a"
    assert app.c == "a"

    app.a = "aa"
    assert app.a == "aa"
    assert app.b == "aa"
    assert app.c == "aa"
