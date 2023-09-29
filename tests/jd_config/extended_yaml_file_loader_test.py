#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from io import StringIO
import logging
from jd_config import MyYamlSafeLoader, YamlObj, ConfigGetter

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG

DATA = """
  a: aa
  b: bb
  c:
    c1: c11
    c2:
      c22: c222
      c23: 23
      c24: 24.24
      c25: 23_000
      c26: true
      c27: false
    c3:
    - 11
    - 22
    - 33
    - 4a
    - c32: c322
"""


def test_yaml_loader():
    file_like_io = StringIO(DATA)
    loader = MyYamlSafeLoader(file_like_io)
    obj = loader.get_single_data()

    assert isinstance(ConfigGetter.get(obj, "a"), YamlObj)
    assert ConfigGetter.get(obj, "a").value == "aa"
    assert ConfigGetter.get(obj, "a").file
    assert ConfigGetter.get(obj, "a").line
    assert ConfigGetter.get(obj, "a").column

    assert ConfigGetter.get(obj, "c.c1").value == "c11"
    assert ConfigGetter.get(obj, "c.c2.c23").value == 23
    assert ConfigGetter.get(obj, "c.c3[1]").value == 22
    assert ConfigGetter.get(obj, "c.c3[4].c32").value == "c322"

    # Only leafs are YamlObj. Containers (Mapping, Sequence) are provided as is.
    assert isinstance(ConfigGetter.get(obj, "c"), dict)
    assert isinstance(ConfigGetter.get(obj, "c.c2"), dict)
    assert isinstance(ConfigGetter.get(obj, "c.c3"), list)
    assert isinstance(ConfigGetter.get(obj, "c.c3[4]"), dict)
