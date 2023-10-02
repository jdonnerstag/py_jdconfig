#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

import logging
from jd_config import ObjectWalker

logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG

DATA = dict(
    a="aa",
    b="bb",
    c=dict(
        c1="c11",
        c2=dict(c22="c222", c23=23, c24=24.24, c25=23_000, c26=True, c27=False),
        c3=[11, 22, 33, "4a", dict(c32="c322")],
    ),
)

def test_objwalk():
    data = list(x.path for x in ObjectWalker.objwalk(DATA, nodes_only=True))
    assert len(data) == 14

    data.remove(("a",))
    data.remove(("b",))
    data.remove(("c", "c1"))
    data.remove(("c", "c2", "c22"))
    data.remove(("c", "c2", "c23"))
    data.remove(("c", "c2", "c24"))
    data.remove(("c", "c2", "c25"))
    data.remove(("c", "c2", "c26"))
    data.remove(("c", "c2", "c27"))

    data.remove(("c", "c3", 0))  # List elements are integer (not string)
    data.remove(("c", "c3", 1))  # List element
    data.remove(("c", "c3", 2))  # List element
    data.remove(("c", "c3", 3))  # List element
    data.remove(("c", "c3", 4, "c32"))

    assert len(data) == 0

# TODO Add test with "skip"
