"""Typed readers for the YAML manifests and JSON artefacts."""

import json
import re
from collections.abc import Iterator
from typing import TypeAlias

import yaml
from yaml.events import (
    AliasEvent,
    DocumentEndEvent,
    DocumentStartEvent,
    Event,
    MappingEndEvent,
    MappingStartEvent,
    ScalarEvent,
    SequenceEndEvent,
    SequenceStartEvent,
    StreamEndEvent,
    StreamStartEvent,
)

YamlValue: TypeAlias = (
    dict[str, "YamlValue"] | list["YamlValue"] | str | int | float | bool | None
)

_TRUE_WORDS = frozenset(
    ('yes', 'Yes', 'YES', 'true', 'True', 'TRUE', 'on', 'On', 'ON')
)
_FALSE_WORDS = frozenset(
    ('no', 'No', 'NO', 'false', 'False', 'FALSE', 'off', 'Off', 'OFF')
)
_NULL_WORDS = frozenset(('', '~', 'null', 'Null', 'NULL'))
_INT = re.compile(
    ''.join((
        r'[-+]?(?:0b[0-1_]+|0[0-7_]+|(?:0|[1-9][0-9_]*)|0x[0-9a-fA-F_]+',
        r'|[1-9][0-9_]*(?::[0-5]?[0-9])+)',
    ))
)
_FLOAT = re.compile(
    ''.join((
        r'[-+]?(?:[0-9][0-9_]*\.[0-9_]*(?:[eE][-+][0-9]+)?',
        r'|\.[0-9_]+(?:[eE][-+][0-9]+)?',
        r'|[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*',
        r'|\.(?:inf|Inf|INF))|[-+]?\.(?:nan|NaN|NAN)',
    ))
)


def load_yaml(text: str) -> YamlValue:
    """Parse a YAML document into plain typed values.

    Args:
        text: YAML source text.

    Returns:
        The document as mappings, sequences and scalars.
    """
    return Parser(yaml.parse(text)).document()


def load_json(text: str) -> YamlValue:
    """Parse a JSON document into plain typed values.

    The strict JSON grammar is validated by json.loads; the values
    themselves come from the YAML event stream, whose events are typed
    where json.loads returns Any.

    Args:
        text: JSON source text.

    Returns:
        The document as mappings, sequences and scalars.
    """
    json.loads(text)
    return load_yaml(text)


def mapping(value: YamlValue) -> dict[str, YamlValue]:
    """Return a document node that must be a mapping.

    Args:
        value: Node read from a document.

    Returns:
        The same value, typed as a mapping.

    Raises:
        TypeError: when the node is not a mapping.
    """
    if not isinstance(value, dict):
        raise TypeError(f'expected a mapping, got {type(value).__name__}')
    return value


def sequence(value: YamlValue) -> list[YamlValue]:
    """Return a document node that must be a sequence.

    Args:
        value: Node read from a document.

    Returns:
        The same value, typed as a sequence.

    Raises:
        TypeError: when the node is not a sequence.
    """
    if not isinstance(value, list):
        raise TypeError(f'expected a sequence, got {type(value).__name__}')
    return value


def text(value: YamlValue) -> str:
    """Return a document node that must be a string.

    Args:
        value: Node read from a document.

    Returns:
        The same value, typed as a string.

    Raises:
        TypeError: when the node is not a string.
    """
    if not isinstance(value, str):
        raise TypeError(f'expected a string, got {type(value).__name__}')
    return value


def integer(value: YamlValue) -> int:
    """Return a document node that must be an integer.

    Args:
        value: Node read from a document.

    Returns:
        The same value, typed as an integer.

    Raises:
        TypeError: when the node is not an integer.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f'expected an integer, got {type(value).__name__}')
    return value


def boolean(value: YamlValue) -> bool:
    """Return a document node that must be a boolean.

    Args:
        value: Node read from a document.

    Returns:
        The same value, typed as a boolean.

    Raises:
        TypeError: when the node is not a boolean.
    """
    if not isinstance(value, bool):
        raise TypeError(f'expected a boolean, got {type(value).__name__}')
    return value


def _scalar(event: ScalarEvent) -> str | int | float | bool | None:
    """Convert one scalar event to its Python value.

    Args:
        event: Scalar event from the parsed stream.

    Returns:
        The scalar value.

    Raises:
        TypeError: when an explicit tag is not part of the core schema.
    """
    if event.tag is None:
        if event.style is not None:
            return event.value
        return _resolve(event.value)
    if event.tag == 'tag:yaml.org,2002:str':
        return event.value
    if event.tag == 'tag:yaml.org,2002:null':
        return None
    if event.tag == 'tag:yaml.org,2002:bool':
        return _resolve_bool(event.value)
    if event.tag == 'tag:yaml.org,2002:int':
        return _to_int(event.value)
    if event.tag == 'tag:yaml.org,2002:float':
        return _to_float(event.value)
    raise TypeError(f'unsupported YAML tag {event.tag}')


def _resolve(value: str) -> str | int | float | bool | None:
    """Resolve an implicit plain scalar with the YAML 1.1 core schema.

    Args:
        value: Plain scalar source text.

    Returns:
        The resolved value.
    """
    if value in _NULL_WORDS:
        return None
    if value in _TRUE_WORDS or value in _FALSE_WORDS:
        return _resolve_bool(value)
    if _INT.fullmatch(value) is not None:
        return _to_int(value)
    if _FLOAT.fullmatch(value) is not None:
        return _to_float(value)
    return value


def _resolve_bool(value: str) -> bool:
    """Resolve one YAML boolean word.

    Args:
        value: Boolean source text.

    Returns:
        The boolean value.

    Raises:
        ValueError: when the text is not a YAML boolean word.
    """
    if value in _TRUE_WORDS:
        return True
    if value in _FALSE_WORDS:
        return False
    raise ValueError(f'not a YAML boolean: {value}')


def _to_int(value: str) -> int:
    """Convert a YAML integer token.

    Args:
        value: Integer source text.

    Returns:
        The integer value.
    """
    digits = value.replace('_', '')
    sign = -1 if digits.startswith('-') else 1
    digits = digits.lstrip('+-')
    if ':' in digits:
        total = 0
        for part in digits.split(':'):
            total = total * 60 + int(part)
        return sign * total
    if digits.startswith('0b'):
        return sign * int(digits[2:], 2)
    if digits.startswith('0x'):
        return sign * int(digits[2:], 16)
    if digits.startswith('0') and len(digits) > 1:
        return sign * int(digits, 8)
    return sign * int(digits)


def _to_float(value: str) -> float:
    """Convert a YAML float token.

    Args:
        value: Float source text.

    Returns:
        The float value.
    """
    digits = value.replace('_', '')
    sign = -1.0 if digits.startswith('-') else 1.0
    digits = digits.lstrip('+-')
    lowered = digits.lower()
    if lowered == '.inf':
        return sign * float('inf')
    if lowered == '.nan':
        return float('nan')
    if ':' in digits:
        total = 0.0
        for part in digits.split(':'):
            total = total * 60 + float(part)
        return sign * total
    return sign * float(digits)


class Parser:
    """Event-stream parser producing plain typed values."""

    def __init__(self, events: Iterator[Event]) -> None:
        """Store the event stream and clear the look-ahead slot.

        Args:
            events: Events yielded by yaml.parse.
        """
        self._events = events
        self._held: Event | None = None

    def seed(self, event: Event) -> None:
        """Hold an event as the next input of the stream.

        Args:
            event: The event returned by the next peek or take.
        """
        self._held = event

    def document(self) -> YamlValue:
        """Parse the single document held by the stream.

        Returns:
            The document value, or None for an empty stream.

        Raises:
            TypeError: when the stream is malformed or holds several
                documents.
        """
        if not isinstance(self._take(), StreamStartEvent):
            raise TypeError('missing YAML stream start')
        event = self.peek()
        if isinstance(event, StreamEndEvent):
            _ = self._take()
            return None
        if not isinstance(event, DocumentStartEvent):
            raise TypeError('missing YAML document start')
        _ = self._take()
        value = self._node()
        if not isinstance(self._take(), DocumentEndEvent):
            raise TypeError('missing YAML document end')
        if not isinstance(self._take(), StreamEndEvent):
            raise TypeError('multiple YAML documents are not supported')
        return value

    def _take(self) -> Event:
        """Return the next event of the stream.

        Returns:
            The next event.
        """
        if self._held is not None:
            event = self._held
            self._held = None
            return event
        return next(self._events)

    def peek(self) -> Event:
        """Return the next event without consuming it.

        Returns:
            The next event.
        """
        if self._held is None:
            self._held = next(self._events)
        return self._held

    def _node(self) -> YamlValue:
        """Parse one node from the stream.

        Returns:
            The node value.

        Raises:
            TypeError: when an alias or an unsupported event is met.
        """
        event = self._take()
        if isinstance(event, ScalarEvent):
            return _scalar(event)
        if isinstance(event, SequenceStartEvent):
            return self._sequence()
        if isinstance(event, MappingStartEvent):
            return self._mapping()
        if isinstance(event, AliasEvent):
            raise TypeError('YAML aliases are not supported')
        raise TypeError(f'unsupported YAML event {type(event).__name__}')

    def _sequence(self) -> list[YamlValue]:
        """Parse the items of a sequence node.

        Returns:
            The parsed items.
        """
        items: list[YamlValue] = []
        while not isinstance(self.peek(), SequenceEndEvent):
            items.append(self._node())
        _ = self._take()
        return items

    def _mapping(self) -> dict[str, YamlValue]:
        """Parse the pairs of a mapping node.

        Returns:
            The parsed pairs.

        Raises:
            TypeError: when a key is not a string or a value cannot be
                parsed.
        """
        pairs: dict[str, YamlValue] = {}
        while not isinstance(self.peek(), MappingEndEvent):
            key = self._node()
            if not isinstance(key, str):
                raise TypeError(f'unsupported mapping key {type(key).__name__}')
            pairs[key] = self._node()
        _ = self._take()
        return pairs
