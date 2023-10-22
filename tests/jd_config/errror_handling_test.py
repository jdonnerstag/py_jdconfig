#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
import os
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pytest

from jd_config import ConfigException, JDConfig, NodeEvent, Placeholder
from jd_config.deep_dict import DeepDict
from jd_config.placeholders import RefPlaceholder

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


def data_dir(*args) -> Path:
    return Path(os.path.join(os.path.dirname(__file__), "data", *args))


def assertTrace(trace_1, path, placeholder = None, file=None) -> None:
    assert trace_1.path == path

    if placeholder:
        if isinstance(placeholder, str):
            assert trace_1.placeholder.path == placeholder
        else:
            assert trace_1.placeholder == placeholder

    if file:
        assert trace_1.file == file


def test_not_found_simple():
    data = DeepDict({})
    try:
        data.get("a")
    except ConfigException as exc:
        assert exc.trace
        assert exc.trace[0].path == ("a",)
        assert exc.trace[0].file is None

    data = DeepDict({"a": "aa", "b": "bb", "c": {"ca": "caa", "cb": {"cba": "cba"}}})
    try:
        data.get("xx")
    except ConfigException as exc:
        assert exc.trace
        assert exc.trace[0].path == ("xx",)
        assert exc.trace[0].file is None

    try:
        data.get("c.xx")
    except ConfigException as exc:
        assert exc.trace
        assert exc.trace[0].path == ("c", "xx")
        assert exc.trace[0].file is None

    try:
        data.get("c.xx.ab")
    except ConfigException as exc:
        assert exc.trace
        assert exc.trace[0].path == ("c", "xx")
        assert exc.trace[0].file is None

    try:
        data.get("xx.aa")
    except ConfigException as exc:
        assert exc.trace
        assert exc.trace[0].path == ("xx",)
        assert exc.trace[0].file is None

    try:
        data.get("c.cb.xx")
    except ConfigException as exc:
        assert exc.trace
        assert exc.trace[0].path == ("c", "cb", "xx")
        assert exc.trace[0].file is None


def test_not_found_ref_same_file():
    data = DeepDict(
        {
            "a": "aa",
            "b": "{ref:x}",
            "c": {"ca": "{ref:x}", "cb": "{ref:c.x}"},
            "d": "{ref:c.cb}",
            "e": "{ref:d}",
        }
    )

    try:
        data.get("b")
    except ConfigException as exc:
        assert isinstance(exc.trace, list) and (len(exc.trace) == 2)
        assert exc.trace[0].path == ("b",)
        assert exc.trace[0].placeholder.path == "x"
        assert exc.trace[0].file is None
        assert exc.trace[1].path == ("x",)
        assert exc.trace[1].placeholder is None
        assert exc.trace[1].file is None

    try:
        data.get("c.ca")
    except ConfigException as exc:
        assert isinstance(exc.trace, list) and (len(exc.trace) == 2)
        assert exc.trace[0].path == ("c", "ca")
        assert exc.trace[0].placeholder.path == "x"
        assert exc.trace[0].file is None
        assert exc.trace[1].path == ("x",)
        assert exc.trace[1].placeholder is None
        assert exc.trace[1].file is None

    try:
        data.get("c.cb")
    except ConfigException as exc:
        assert isinstance(exc.trace, list) and (len(exc.trace) == 2)
        assert exc.trace[0].path == ("c", "cb")
        assert exc.trace[0].placeholder.path == "c.x"
        assert exc.trace[0].file is None
        assert exc.trace[1].path == ("c", "x")
        assert exc.trace[1].placeholder is None
        assert exc.trace[1].file is None

    try:
        data.get("d")
    except ConfigException as exc:
        assert isinstance(exc.trace, list) and (len(exc.trace) == 3)
        assert exc.trace[0].path == ("d",)
        assert exc.trace[0].placeholder.path == "c.cb"
        assert exc.trace[0].file is None
        assert exc.trace[1].path == ("c", "cb")
        assert exc.trace[1].placeholder.path == "c.x"
        assert exc.trace[1].file is None
        assert exc.trace[2].path == ("c", "x")
        assert exc.trace[2].placeholder is None
        assert exc.trace[2].file is None


def test_not_found_import():
    # config-5 has plenty errors

    cfg = JDConfig(ini_file=None)
    cfg.ini["env"] = None  # Make sure, we are not even trying to load an env file
    cfg.ini["config_dir"] = data_dir("configs-5")  # configure the directory for imports
    data = cfg.load("config.yaml")
    assert data

    try:
        data.get("b")
    except ConfigException as exc:
        assert isinstance(exc.trace, list) and (len(exc.trace) == 2)
        assertTrace(exc.trace[0], ("b",), "x", None)
        assertTrace(exc.trace[1], ("x",), None, None)

    try:
        data.get("c.b")
    except ConfigException as exc:
        assert isinstance(exc.trace, list) and (len(exc.trace) == 2)
        assertTrace(exc.trace[0], ("c","b"), "x", None)
        assertTrace(exc.trace[1], ("x",), None, None)

    try:
        data.get("c.c")
    except ConfigException as exc:
        assert isinstance(exc.trace, list) and (len(exc.trace) == 2)
        assertTrace(exc.trace[0], ("c","c"), "x", None)
        assertTrace(exc.trace[1], ("x",), None, None)

    try:
        data.get("c.d")
    except ConfigException as exc:
        assert isinstance(exc.trace, list) and (len(exc.trace) == 3)
        assertTrace(exc.trace[0], ("c","d"), "b", None)
        assertTrace(exc.trace[1], ("b",), "x", None)
        assertTrace(exc.trace[2], ("x",), None, None)

    try:
        data.get("c.e")
    except ConfigException as exc:
        assert isinstance(exc.trace, list) and (len(exc.trace) == 3)
        assertTrace(exc.trace[0], ("c","e"), "c.b", None)
        assertTrace(exc.trace[1], ("c","b"), "x", None)
        assertTrace(exc.trace[2], ("x",), None, None)


def test_not_found_env():
    # TODO
    pass


def test_not_found_global():
    # TODO
    pass


def test_not_found_question_mark():
    # TODO
    pass
