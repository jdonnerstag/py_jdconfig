#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Manage everything related to placeholders, such as
```
  db_engine: '{ref: db.engine, innodb}'
```

Placeholders can only occur in yaml values. They are not allowed in keys.
And it must be a yaml *string* value, surrounded by quotes.
"""

import logging
from dataclasses import dataclass
from typing import Any, Iterator, Union, List
from .jd_config import CompoundValue, ConfigException

__parent__name__ = __name__.rpartition('.')[0]
logger = logging.getLogger(__parent__name__)


ValueType: type = Union[int, float, bool, str, 'Placeholder']

@dataclass
class Placeholder:
    """A common base class for all Placeholders
    """
    name: str
    args: List[ValueType]


@dataclass
class ImportPlaceholder(Placeholder):
    """Import Placeholder: '{import: <file>[, <replace=False>]}'
    """

    @property
    def file(self) -> str:
        """The 1st argument: the yaml file to import"""
        return self.args[0]

    @property
    def env(self) -> str | None:
        """The 2nd argument: the environment, e.g. dev, test, prod"""

        if len(self.args) > 1:
            return self.args[1]
        return None

    @property
    def replace(self) -> bool:
        """The 3rd argument: False - replace yaml value; True - merge with parent container
        """

        if len(self.args) > 2:
            return bool(self.args[2])
        return False


@dataclass
class RefPlaceholder(Placeholder):
    """Reference Placeholder: '{ref: <path>[, <default>]}'
    """

    @property
    def path(self) -> str:
        """The 1st argument: path to the reference element"""
        return self.args[0]

    @property
    def default(self) -> str | None:
        """The 2nd argument: A default value'"""

        if len(self.args) > 1:
            return self.args[1]
        return None


class ValueReaderException(ConfigException):
    """Denote an Exception that occured while parsing a yaml value (wiht placeholder)"""

class ValueReader:
    """Parse a yaml value
    """

    def parse(self, strval: str, sep: str = ",") -> Iterator[ValueType]:
        """Parse a yaml value and yield the various parts.

        :param strval: Input yaml string value
        :param sep: argument separator. Default: ','
        :return: Generator yielding individual parts of the yaml string value
        """

        stack: List[Placeholder] = []
        _iter = self.tokenize(strval, sep)
        try:
            while text := next(_iter, None):
                if text == "{":
                    name = next(_iter)
                    colon = next(_iter)
                    assert colon == ":"
                    placeholder = Placeholder(name, [])
                    if name == "import":
                        placeholder.__class__ = ImportPlaceholder
                    elif name == "ref":
                        placeholder.__class__ = RefPlaceholder
                    stack.append(placeholder)
                elif text == "}" and stack:
                    placeholder = stack.pop()
                    if not stack:
                        yield placeholder
                    else:
                        stack[-1].args.append(placeholder)
                elif isinstance(text, str) and text.find("{") != -1:
                    values = list(ValueReader().parse(text))
                    values = [self.convert(x) for x in values]
                    value = CompoundValue(values)
                    if not stack:
                        yield value
                    else:
                        stack[-1].args.append(value)

                else:
                    if not stack:
                        yield text
                    else:
                        value = self.convert(text)
                        stack[-1].args.append(value)

        except StopIteration as exc:
            raise ValueReaderException(
                f"Failed to parse yaml value with placeholder: '${strval}'") from exc


    def tokenize(self, strval: str, sep: str = ",") -> Iterator[str]:
        """Tokenize the yaml string value

        :param strval: Input yaml string value
        :param sep: argument separator. Default: ','
        :return: Generator yielding individual string tokens
        """

        start = 0
        i = 0
        while i < len(strval):
            c = strval[i]
            if c == "\\":
                i += 1
            elif c in ['"', "'"]:
                i = self.find_closing_quote(strval, i)
                value = strval[start + 2 : i]
                yield value
                start = i + 1
            elif c in [sep, "{", "}", ":"]:
                value = strval[start : i].strip()
                if value:
                    yield value
                start = i + 1

                if c is not sep:
                    yield c

            i += 1

        value = strval[start : ].strip()
        if value:
            yield value


    def find_closing_quote(self, strval: str, start: int) -> int:
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


    def convert(self, strval: Any) -> int | float | str | bool:
        """Convert a string into int, float or bool of possible, else
        return the string value.

        :param strval: Input yaml string value
        """
        if isinstance(strval, str):
            possible = [convert_bool, int, float, str]
            for func in possible:
                try:
                    return func(strval)
                except (ValueError, KeyError):
                    continue

        return strval


def convert_bool(strval: str) -> bool:
    """Convert a string into a bool, if possible. Else throw an Exception.

    :param strval: Input yaml string value
    """
    bool_vals = {
        "false": False,
        "no": False,
        "0": False,
        "true": True,
        "yes": True,
        "1": True,
    }

    if len(strval) > 5:
        raise ValueError(strval)

    text = strval.lower()
    return bool_vals[text]
