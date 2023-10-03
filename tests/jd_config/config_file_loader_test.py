#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# pylint: disable=C

from io import StringIO
import os
from pathlib import Path
import logging
from typing import Mapping
from jd_config import ConfigFileLoader
from jd_config import ResolverMixin


logger = logging.getLogger(__name__)

# Notes:
# show logs: pytest --log-cli-level=DEBUG


class MyMixinTestClass(ResolverMixin):
    def __init__(self) -> None:
        self.data = None

        ResolverMixin.__init__(self)

        # Why this approach and not a Mixin/Base Class. ConfigFileLoader
        # is comparatively large with a number of functions. Functions
        # which I consider private, but python has not means to mark them
        # private. This is a more explicit approach.
        self.config_file_loader = ConfigFileLoader()

    # TODO This is repetitive => create a little mixin
    def load(
        self, fname: Path | StringIO, config_dir: Path | None, env: str | None = None
    ) -> Mapping:
        self.data = self.config_file_loader.load(fname, config_dir, env)
        return self.data


def data_dir(*args) -> Path:
    path = os.path.join(os.path.dirname(__file__), "data", *args)
    path = Path(path).relative_to(Path.cwd())
    return path


def test_load_jdconfig_1():
    # config-1 contains a simple config file, with no imports.

    cfg = MyMixinTestClass()
    data = cfg.load(Path("config.yaml"), config_dir=data_dir("configs-1"))
    assert data

    # With an absolute filename, the config_dir is ignored. Which however
    # only works as long as no {import: ..} placeholders are used.
    cfg = MyMixinTestClass()
    file = data_dir("configs-1", "config.yaml")
    data = cfg.load(file.absolute(), config_dir=Path("/this/likely/does/not/exist"))
    assert data

    # It shouldn't matter
    data = cfg.load(file.absolute(), config_dir=None)
    assert data
