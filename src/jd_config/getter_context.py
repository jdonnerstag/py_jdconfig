#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TYPE_CHECKING

from .config_path import CfgPath
from .utils import ConfigException, ContainerType, new_trace

if TYPE_CHECKING:
    from .placeholders import Placeholder

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)

OnMissing = Callable[["GetterContext", Exception], Any]

GetterFn = Callable[[Any, str | int, "GetterContext", Callable[[], "GetterFn"]], Any]


# pylint: disable=too-many-instance-attributes
@dataclass
class GetterContext:
    """The current context while walking a deep structure"""

    # Current parent container
    data: ContainerType

    # Current key to retrieve the element from the parent
    # Note that 'key' may not be 'path[idx]'
    key: str | int | None = None

    # Normalized full path as provided by the user
    # CfgPath is derived from list, and thus should be created with a factory.
    path: CfgPath = field(default_factory=CfgPath)

    # While walking, the current index within the path
    idx: int = 0

    # Callback function if key could not be found
    on_missing: Optional[OnMissing] = None

    # While walking, the yaml file associated with the container
    current_file: Optional[ContainerType] = None

    # The global (main) yaml file
    global_file: Optional[ContainerType] = None

    # I'm not a fan of dynamically adding attributes to a class.
    # Arbitrary attributes which extensions may require.
    args: Optional[dict] = None

    getter_pipeline: tuple[GetterFn] = field(default_factory=tuple)

    # internal: detect recursions
    memo: Optional[list] = None

    def __post_init__(self) -> None:
        if self.current_file is None:
            self.current_file = self.data

        if self.global_file is None:
            self.global_file = self.current_file

    @property
    def value(self) -> Any:
        """Given the current 'key', get the value from the underlying container"""
        return self.data[self.key]

    def cur_path(self) -> CfgPath:
        """While walking, the path to the current element"""
        # self.path might as well be a CfgPath or ExtendedCfgPath !!
        return type(self.path)(self.path[: self.idx] + (self.key,))

    def parent_path(self, offset: int) -> CfgPath:
        """While walking, the path to the N-th parent element"""
        # self.path might as well be a CfgPath or ExtendedCfgPath !!
        return type(self.path)(self.path[: self.idx - offset])

    def path_replace(self, replace, count=1) -> CfgPath:
        """Replace the path element(s) at the current position (idx), with
        the new ones provided.
        """
        if isinstance(replace, CfgPath):
            replace = replace.path

        if not isinstance(replace, tuple):
            replace = (replace,)

        # self.path might as well be a CfgPath or ExtendedCfgPath !!
        return type(self.path)(
            self.path[: self.idx] + replace + self.path[self.idx + count :]
        )

    def add_memo(self, placeholder: "Placeholder") -> None:
        """Identify recursions"""

        if self.memo is None:
            self.memo = []

        if placeholder in self.memo:
            self.memo.append(placeholder)
            raise ConfigException(f"Config recursion detected: {self.memo}")

        self.memo.append(placeholder)

    def exception(self, msg) -> ConfigException:
        """Create a ConfigException and automatically add a trace"""
        trace = new_trace(ctx=self)
        return ConfigException(msg, trace=trace)
