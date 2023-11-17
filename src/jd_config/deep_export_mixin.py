#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Mixin to export deep config data
"""

import logging
from typing import Optional

import yaml

from .base_model import BaseModel
from .config_path import PathType
from .utils import ContainerType

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepExportMixin:
    """A mixin to export configs into dict or yaml structures.

    Dependencies:
    - self.data: the config object structure
    - self.resolve(): a method to lazily resolve placeholders
    - self.get(): acces a (deep) config node
    """

    def to_dict(self, path: Optional[PathType] = None) -> dict | list:
        """Walk the config items with an optional starting point, and create a
        dict from it.
        """
        if path is not None:
            return self.get(path).to_dict()

        if self.is_mapping():
            return self._to_dict_dict()
        if self.is_sequence():
            return self._to_dict_list()

        raise AttributeError(f"Expected a ContainerType: '{self.data}'")

    def _to_dict_dict(self) -> dict:
        rtn = {}
        for k, v in self.items():
            if isinstance(v, ContainerType):
                child = self.clone(v, k)
                rtn[k] = child.to_dict()
            elif isinstance(v, BaseModel):
                rtn[k] = child.to_dict()
            else:
                # Make sure we resolve or whatever else is necessary
                rtn[k] = self.get(k)

        return rtn

    def _to_dict_list(self) -> list:
        rtn = []
        for i, v in self.items():
            if isinstance(v, ContainerType):
                child = self.clone(v, i)
                rtn.append(child.to_dict())
            elif isinstance(v, BaseModel):
                rtn.append(child.to_dict())
            else:
                rtn.append(v)

        return rtn

    def to_yaml(self, path: Optional[PathType] = None, stream=None, **kvargs):
        """Convert the configs (or part of it), into a yaml document"""

        data = self.to_dict(path)
        return yaml.dump(data, stream, **kvargs)
