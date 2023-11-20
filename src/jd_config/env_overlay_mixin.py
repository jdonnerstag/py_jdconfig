#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
A mixin that ...
"""

import logging
from typing import Any, Optional, Self

from jd_config.base_model import BaseModel

from .config_path import CfgPath
from .utils import ContainerType

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class EnvOverlayMixin:
    """A mixin that ..."""

    def __init__(
        self,
        data: ContainerType,
        path: Optional[CfgPath] = None,
        *,
        env_data: Optional[BaseModel] = None,
        env: Optional[str] = None,
        **kvargs,
    ) -> None:
        super().__init__(data, path, **kvargs)

        self.env_data = env_data
        self.env = env

    def clone(self, data, key) -> Self:
        rtn = super().clone(data, key)
        rtn.env = self.env
        # Note: we are copying the *root* env node!!
        rtn.env_data = self.env_data
        return rtn

    # @override
    def _get(
        self,
        path: CfgPath,
        **kvargs,
    ) -> (Any, CfgPath):
        """..."""
        if self.env_data:
            try:
                value = self.get_from_env_data(path)
                return value, path[1:]
            except KeyError:
                pass  # Not value found

        return super()._get(path, **kvargs)

    def get_from_env_data(self, path: CfgPath):
        key = path[0]
        path = self.cur_path(key)  # The env_data is always the env root
        data = self.env_data.get(path)
        if isinstance(data, BaseModel):
            raise KeyError(repr(path))

        return data
