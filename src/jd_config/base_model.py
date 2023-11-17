#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Load config settings from *.ini
"""

import logging
from typing import Any, Callable, Iterator, Mapping, Optional, Self, Sequence

from .config_path import CfgPath, PathType
from .utils import DEFAULT, ConfigException, ContainerType, NonStrSequence

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class BaseModel:
    """A wrapper around the config/setting object"""

    path_type = CfgPath

    def __init__(
        self,
        data: ContainerType,
        key: str | int | None = None,
        *,
        parent: Optional["BaseModel"] = None,
        local_root: bool = False,
        **_,
    ) -> None:
        if not isinstance(data, ContainerType):
            raise ConfigException(f"Not a ContainerType: '{data}'")

        self.data = data
        self.key = key
        self.parent = parent
        self.is_local_root = parent is None or local_root

    def clone(self, data, key) -> Self:
        return type(self)(data, key, parent=self)

    def get_global_root(self):
        if self.parent is None:
            return self

        return self.parent.get_global_root()

    def get_local_root(self):
        if self.parent is None or self.is_local_root:
            return self

        return self.parent.get_local_root()

    def path(self, key: Optional[str | int | Sequence[str | int]] = None) -> CfgPath:
        rtn = []
        obj = self
        while obj.parent is not None:
            rtn.append(obj.key)
            obj = obj.parent

        rtn.reverse()
        if isinstance(key, NonStrSequence):
            rtn.extend(key)
        elif key is not None:
            rtn.append(key)

        return CfgPath(rtn)

    def get(
        self,
        path: PathType,
        default=DEFAULT,
        *,
        on_missing: Optional[Callable] = None,
        **kvargs,
    ) -> Any:
        if on_missing is None:
            on_missing = self.on_missing

        path = self.path_type(path)
        if not path:
            return self

        try:
            value, rest_path = self._get(path, on_missing=on_missing, **kvargs)

            if not rest_path:
                if isinstance(value, ContainerType):
                    value = self.clone(value, path[0])

                return value

            if not isinstance(value, BaseModel):
                if not isinstance(value, ContainerType):
                    raise ConfigException(f"Expected a ContainerType: '{value}'")

                child = self.clone(value, path[0])
            else:
                child = value

            return child.get(rest_path, on_missing=on_missing, **kvargs)
        except KeyError:
            if default is DEFAULT:
                raise

            return default

    def _get(
        self, path: CfgPath, *, on_missing: Callable, **kvargs
    ) -> (Any, CfgPath):
        key = path[0]

        if key == CfgPath.CURRENT_DIR:
            return self, path[1:]

        if key == CfgPath.PARENT_DIR:
            if self.parent is None:
                raise KeyError(f"Reached the root. No parent found: '{self}'")

            return self.parent, path[1:]

        try:
            try:
                value = self.data[key]
            except (IndexError, TypeError) as exc:
                raise KeyError(str(exc)) from exc
        except KeyError as exc:
            cur_path = self.path(key)
            if not callable(on_missing):
                raise

            value = on_missing(self.data, key, cur_path, exc, **kvargs)
            self.data[key] = value

        return value, path[1:]

    def on_missing(self, data, key, cur_path, exc) -> Any:
        raise exc

    def __getitem__(self, key: Any) -> Any:
        return self.get(key)

    # def __setitem__(self, key: Any, item: Any) -> None:
    #    self.set(key, item)

    # def __delitem__(self, key: Any) -> None:
    #    self.delete(key, exception=True)

    def __len__(self) -> int:
        return self.data.__len__()

    def is_mapping(self) -> bool:
        return isinstance(self.data, Mapping)

    def is_sequence(self) -> bool:
        return isinstance(self.data, NonStrSequence)

    def items(self) -> Iterator[tuple[str | int, Any]]:
        if self.is_mapping():
            return self.data.items()

        if self.is_sequence():
            return enumerate(self.data)

        raise ConfigException(f"Bug? Don't how to iterate over: '{self.data}'")

    def __eq__(self, other: Mapping) -> bool:
        return self.data == other

    def __repr__(self) -> str:
        return self.data.__repr__()  # TODO improve

    def __str__(self) -> str:
        return self.data.__str__()  # TODO improve