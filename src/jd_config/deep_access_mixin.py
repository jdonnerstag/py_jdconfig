#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Provide getter and setter to access deep config structures.
"""

import logging
from typing import Any, Iterator, Optional
from .objwalk import ObjectWalker, NodeEvent
from .config_getter import ConfigGetter, PathType, DEFAULT
from .extended_yaml_file_loader import YamlObj


__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class DeepAccessMixin:
    """A mixin that provides getters and setter to access deep config structures

    Dependencies:
    - self.data: the config object structure
    - self.resolve(): a method to lazily resolve placeholders
    """

    def __init__(self) -> None:
        assert hasattr(self, "data"), "Mixin depends on self.data"
        assert hasattr(self, "resolve"), "Mixin depends on self.resolve()"

    def get(self, path: PathType, default: Any = DEFAULT, *, sep: str = ".") -> Any:
        """Similar to dict.get(), but with deep path support.

        Placeholders are automatically resolved.
        Mappings and Sequences are returned as is.
        """

        obj = ConfigGetter().get(self.data, path, default=default, sep=sep)
        if not isinstance(obj, YamlObj):
            return obj

        value = self.resolve(obj.value, self.data)
        return value

    def delete(self, path: PathType, *, sep: str = ".", exception: bool = True) -> Any:
        """Similar to 'del dict[key]', but with deep path support"""
        return ConfigGetter().delete(self.data, path, sep=sep, exception=exception)

    def set(
        self,
        path: PathType,
        value: Any,
        *,
        create_missing: [callable, bool, dict] = True,
        sep: str = "."
    ) -> Any:
        """Similar to 'dict[key] = valie', but with deep path support.

        Limitations:
          - is not possible to append elements to a Sequence. You need to get() the list
            and manually append the element.
        """

        return ConfigGetter().set(
            self.data, path, value, create_missing=create_missing, sep=sep
        )

    def walk(
        self, root: Optional[PathType] = None, resolve: bool = True
    ) -> Iterator[NodeEvent]:
        """Walk the config items with an optional starting point

        :param root: An optional starting point.
        :param resolve: If true (default), then resolve all Placeholders
        :return: Generator, yielding a Tuple
        """

        obj = self.data
        if root:
            obj = self.get(root)

        for event in ObjectWalker.objwalk(obj, nodes_only=True):
            if resolve:
                event.value = self.resolve(event.value.value, self.data)

            yield event
