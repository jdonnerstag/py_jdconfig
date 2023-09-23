#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
from dataclasses import dataclass
from typing import Any, Iterator, Union, List
from .jd_config import CompoundValue

logger = logging.getLogger(__name__)


ValueType: type = Union[int, float, bool, str, 'Placeholder']

@dataclass
class Placeholder:
    name: str
    args: List[ValueType]

@dataclass
class ImportPlaceholder(Placeholder):

    @property
    def file(self) -> str:
        return self.args[0]

    @property
    def env(self) -> str | None:
        if len(self.args) > 1:
            return self.args[1]
        return None

    @property
    def replace(self) -> bool:
        if len(self.args) > 2:
            return bool(self.args[2])
        return False


@dataclass
class RefPlaceholder(Placeholder):

    @property
    def path(self) -> str:
        return self.args[0]

    @property
    def default(self) -> str | None:
        if len(self.args) > 1:
            return self.args[1]
        return None


class ValueReaderException(Exception):
    pass

class ValueReader:

    def parse(self, strval: str, sep: str = ",") -> Iterator[ValueType]:
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


    def convert(self, strval: Any) -> int | float | str:
        if isinstance(strval, str):
            possible = [convert_bool, int, float, str]
            for func in possible:
                try:
                    return func(strval)
                except (ValueError, KeyError):
                    continue

        return strval


def convert_bool(strval: str) -> bool:
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
