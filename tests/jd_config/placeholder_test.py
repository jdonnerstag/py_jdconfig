#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from dataclasses import dataclass
from io import StringIO
import logging
import os
from pathlib import Path
import re
from typing import Mapping

import pytest
from jd_config import RefPlaceholder, ImportPlaceholder, EnvPlaceholder
from jd_config import ResolverMixin, DeepAccessMixin, ConfigFileLoader
from jd_config import ConfigException, Placeholder, NodeEvent

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def test_ImportPlaceholder():
    obj = ImportPlaceholder(file="xxx")
    assert obj.file == "xxx"

    # Filename is missing
    with pytest.raises(Exception):
        ImportPlaceholder(file="")


def test_RefPlaceholder():
    obj = RefPlaceholder(path="db")
    assert obj.path == "db"
    assert obj.default_val is None

    # Filename is missing
    with pytest.raises(Exception):
        RefPlaceholder(path="")


def test_EnvPlaceholder():
    obj = EnvPlaceholder(env_var="ENV")
    assert obj.env_var == "ENV"
    assert obj.default_val is None

    # Filename is missing
    with pytest.raises(Exception):
        EnvPlaceholder(env_var="")


def test_resolve():
    cfg = {
        "a": "aa",
        "b": "{ref:a}",
        "c": "{ref:b}",
        "d": "{ref:xxx}",
    }

    resolver = ResolverMixin()
    ref = RefPlaceholder("a")
    assert ref.resolve(resolver, cfg) == "aa"

    ref = RefPlaceholder("b")
    assert ref.resolve(resolver, cfg) == "aa"

    ref = RefPlaceholder("c")
    assert ref.resolve(resolver, cfg) == "aa"

    with pytest.raises(ConfigException):
        ref = RefPlaceholder("d")
        ref.resolve(resolver, cfg)

    with pytest.raises(ConfigException):
        ref = RefPlaceholder("xxx")
        ref.resolve(resolver, cfg)


@dataclass
class MyBespokePlaceholder(Placeholder):
    # This is also a test for a placeholder that does not take any parameters

    def resolve(self, *_, **__):
        return "it's me"


def test_bespoke_placeholder():
    cfg = {
        "a": "{ref:b}",
        "b": "{bespoke:}",
    }

    resolver = ResolverMixin()
    resolver.register_placeholder_handler("bespoke", MyBespokePlaceholder)
    ref = RefPlaceholder("a")
    assert ref.resolve(resolver, cfg) == "it's me"


def test_mandatory_value():
    cfg = {
        "a": "???",
        "b": "{ref:a}",
    }

    resolver = ResolverMixin()
    ref = RefPlaceholder("a")
    with pytest.raises(ConfigException):
        assert ref.resolve(resolver, cfg)

    ref = RefPlaceholder("b")
    with pytest.raises(ConfigException):
        assert ref.resolve(resolver, cfg)


def test_detect_recursion():
    cfg = {
        "a": "{ref:b}",
        "b": "{ref:c}",
        "c": "{ref:a}",
    }

    resolver = ResolverMixin()
    ref = RefPlaceholder("a")
    with pytest.raises(ConfigException):
        assert ref.resolve(resolver, cfg)
