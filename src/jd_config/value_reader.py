#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Manage everything related to placeholders, such as
```
  db_user: '{env: DB_USER, ???}'
  db_engine: '{ref: db.engine, innodb}'
```

Placeholders can only occur in yaml values. They are not allowed in keys.
And it must be a yaml *string* value, surrounded by quotes.
"""

import logging
from typing import Iterator, Optional, Union
from .config_getter import ConfigException
from .string_converter_mixin import StringConverterMixin
from .placeholders import (
    Placeholder,
    ImportPlaceholder,
    RefPlaceholder,
    EnvPlaceholder,
    TimestampPlaceholder,
)

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


ValueType = Union[int, float, bool, str, Placeholder]


class ValueReaderException(ConfigException):
    """Denote an Exception that occured while parsing a yaml value (with placeholder)"""


class ValueReader(StringConverterMixin):
    """Maintain a registry of supported placeholders and parse a yaml value
    into its constituent parts
    """

    def __init__(self, registry: Optional[dict[str, Placeholder]] = None) -> None:
        self.registry = registry

        if not registry:
            self.registry = {
                "ref": RefPlaceholder,
                "import": ImportPlaceholder,
                "env": EnvPlaceholder,
                "timestamp": TimestampPlaceholder,
            }


    def parse(self, strval: str, *, sep: str = ",") -> Iterator[ValueType]:
        """Parse a yaml value and yield the various parts.

        :param strval: Input yaml string value
        :param sep: argument separator. Default: ','
        :return: Generator yielding individual parts of the yaml string value
        """

        _iter = self.tokenize(strval, sep)
        try:
            while text := next(_iter, None):
                if text == sep:
                    pass
                elif text == "{":
                    placeholder = self.parse_placeholder(_iter, sep)
                    yield placeholder
                elif isinstance(text, str) and text.find("{") != -1:
                    values = list(self.parse(text))
                    value = list(self.convert(x) for x in values)
                    yield value
                else:
                    value = self.convert(text)
                    yield value

        except StopIteration as exc:
            raise ValueReaderException(
                f"Failed to parse yaml value with placeholder: '${strval}'"
            ) from exc


    def parse_placeholder(self, _iter: Iterator, sep: str) -> Placeholder:
        """Parse {<name>: <arg-1>, ...} into registered Placeholder objects"""

        name = next(_iter)
        args = []
        compound = []

        colon = next(_iter)
        assert colon == ":"

        while text := next(_iter, None):
            if text in [sep, "}"]:
                if len(compound) == 1:
                    args.append(compound[0])
                elif len(compound) > 1:
                    args.append(list(compound))
                compound.clear()

            if text == "{":
                placeholder = self.parse_placeholder(_iter, sep)
                compound.append(placeholder)
            elif text == "}":
                placeholder = self.registry[name](*args)
                return placeholder
            elif text != sep:
                if isinstance(text, str) and text.find("{") != -1:
                    value = list(self.parse(text))
                    value = [self.convert(x) for x in value]
                else:
                    value = self.convert(text)

                compound.append(value)

        raise ConfigException(f"Unexpected end: '{text}'")


    @classmethod
    def tokenize(cls, strval: str, sep: str = ",") -> Iterator[str]:
        """Tokenize the yaml string value

        :param strval: Input yaml string value
        :param sep: argument separator. Default: ','
        :return: Generator yielding individual string tokens
        """

        start = 0
        i = 0
        while i < len(strval):
            ch = strval[i]  # pylint: disable=invalid-name
            if ch == "\\":
                i += 1
            elif ch in ['"', "'"]:
                i = cls.find_closing_quote(strval, i)
                value = strval[start + 2 : i]
                yield value
                start = i + 1
            elif ch in [sep, "{", "}", ":"]:
                value = strval[start:i].strip()
                if value:
                    yield value

                start = i + 1
                yield ch

            i += 1

        value = strval[start:].strip()
        if value:
            yield value


    @classmethod
    def find_closing_quote(cls, strval: str, start: int) -> int:
        """Given a start position, determine the end of a quote.

        The first character determine the quote, e.g. "'", '"'

        :param strval: Input yaml string value
        :param start: position where the quote starts
        :return: position where the quote ends
        """

        quote_char = strval[start]
        i = start + 1
        while i < len(strval):
            char = strval[i]
            if char == "\\":
                i += 1
            elif char == quote_char:
                return i

            i += 1

        return i - 1
