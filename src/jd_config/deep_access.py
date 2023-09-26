#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Main config package to load and access config values.
"""

import logging
from typing import Any, Iterator,  Mapping, Optional
import yaml
from .placeholder import Placeholder, ValueReader
from .objwalk import objwalk, NodeEvent, NewMappingEvent, NewSequenceEvent, DropContainerEvent
from .config_getter import ConfigGetter, ConfigException, PathType, DEFAULT
from .yaml_loader import YamlObj


__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)


class DeepAccessMixin:
    """A mixin that provides getters and setter for the configuration
    """

    def __init__(self) -> None:

        # Read string into Placeholders ...
        self.value_reader = ValueReader()


    def register_placeholder(self, name: str, type_: type) -> None:
        """Register (add or replace) a placeholder handler
        """

        self.value_reader.registry[name] = type_


    def resolve(self, value: Any, _data: Optional[Mapping] = None):
        """Lazily resolve Placeholders

        Yaml values may contain our Placeholder. Upon loading a yaml file,
        a CompoundValue will be created, for every yaml value that contains
        a Placeholder. resolve() lazily resolves the placeholders and joins
        the pieces together for the actuall yaml value.
        """

        key = value
        if isinstance(value, Placeholder):
            value = value.resolve(_data)

        if isinstance(value, list):
            value = [self.resolve(x, _data) for x in value]
            value = "".join(value)
            return value

        if value == "???":
            raise ConfigException(f"Mandatory config value missing: '${key}'")

        if isinstance(value, (str, int, float, bool)):
            return value

        raise ConfigException(f"Unable to resolve: '${value}'")


    def get(self, path: PathType, default: Any = DEFAULT, *, sep: str=".") -> Any:
        """Similar to dict.get(), but with deep path support.

        Placeholders are automatically resolved.
        Mappings and Sequences are returned as is.
        """

        obj = ConfigGetter.get(self.data, path, default=default, sep=sep)
        if not isinstance(obj, YamlObj):
            return obj

        value = self.resolve(obj.value, self.data)
        return value


    def delete(self, path: PathType, *, sep: str=".", exception: bool = True) -> Any:
        """Similar to 'del dict[key]', but with deep path support
        """
        return ConfigGetter.delete(self.data, path, sep=sep, exception=exception)


    def set(self, path: PathType, value: Any, *, create_missing: [callable, bool, dict]=True, sep: str=".") -> Any:
        """Similar to 'dict[key] = valie', but with deep path support.

        Limitations:
          - is not possible to append elements to a Sequence. You need to get() the list
            and manually append the element.
        """

        return ConfigGetter.set(self.data, path, value, create_missing=create_missing, sep=sep)


    def walk(self, root: Optional[PathType] = None, resolve: bool = True
        ) -> Iterator[NodeEvent]:
        """Walk the config items with an optional starting point

        :param root: An optional starting point.
        :param resolve: If true (default), then resolve all Placeholders
        :return: Generator, yielding a Tuple
        """

        obj = self.data
        if root:
            obj = self.get(root)

        for event in objwalk(obj, nodes_only=True):
            if resolve:
                event.value = self.resolve(event.value.value, self.data)

            yield event


    def to_dict(self, root: Optional[PathType] = None, resolve: bool = True) -> dict:
        """Walk the config items with an optional starting point, and create a
        dict from it.
        """

        obj = self.data
        if root:
            obj = self.get(root)

        stack = []
        for event in objwalk(obj, nodes_only=False):
            if isinstance(event, (NewMappingEvent, NewSequenceEvent)):
                if isinstance(event, NewMappingEvent):
                    new = {}
                else:
                    new = []
                stack.append(new)
                if event.path:
                    if isinstance(cur, Mapping):
                        cur[event.path[-1]] = new
                    else:
                        cur.append(new)
                cur = new
            elif isinstance(event, DropContainerEvent):
                stack.pop()
                if stack:
                    cur = stack[-1]
            elif isinstance(event, NodeEvent):
                value = event.value
                if resolve:
                    value = self.resolve(event.value.value, self.data)

                if isinstance(cur, Mapping):
                    cur[event.path[-1]] = value
                else:
                    cur.append(value)

        return cur

    def to_yaml(self, root: Optional[PathType] = None, stream = None, **kvargs):
        """Convert the configs (or part of it), into a yaml document
        """

        data = self.to_dict(root, resolve=True)
        return yaml.dump(data, stream, **kvargs)
