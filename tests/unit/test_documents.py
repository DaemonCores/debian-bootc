"""Unit tests for the typed YAML and JSON readers."""

import math

import pytest
from yaml.events import (
    DocumentStartEvent,
    Event,
    ScalarEvent,
    StreamEndEvent,
    StreamStartEvent,
)

from tests.support.documents import (
    Parser,
    YamlValue,
    boolean,
    integer,
    load_yaml,
    mapping,
    sequence,
    text,
)


def _parse_stream(events: list[Event]) -> YamlValue:
    """Parse a synthetic event stream.

    Args:
        events: Events handed to the parser, in stream order.

    Returns:
        The parsed document value.
    """
    parser: Parser = Parser(iter(events))
    return parser.document()


def test_mapping_rejects_a_non_mapping() -> None:
    """A sequence node is not accepted where a mapping is required."""
    with pytest.raises(TypeError, match='expected a mapping, got list'):
        _ = mapping([])


def test_sequence_rejects_a_non_sequence() -> None:
    """A mapping node is not accepted where a sequence is required."""
    with pytest.raises(TypeError, match='expected a sequence, got dict'):
        _ = sequence({})


def test_text_rejects_a_non_string() -> None:
    """An integer node is not accepted where a string is required."""
    with pytest.raises(TypeError, match='expected a string, got int'):
        _ = text(1)


def test_integer_rejects_bool_and_other_nodes() -> None:
    """Booleans are not integers and strings are not integers either."""
    with pytest.raises(TypeError, match='expected an integer, got bool'):
        _ = integer(True)
    with pytest.raises(TypeError, match='expected an integer, got str'):
        _ = integer('1')
    assert integer(7) == 7


def test_boolean_rejects_a_non_boolean() -> None:
    """An integer node is not accepted where a boolean is required."""
    with pytest.raises(TypeError, match='expected a boolean, got int'):
        _ = boolean(0)
    assert boolean(False) is False


def test_explicit_core_tags_are_honoured() -> None:
    """Every core-schema tag resolves to its declared type."""
    assert load_yaml('!!str 12') == '12'
    assert load_yaml('!!null ""') is None
    assert load_yaml('!!bool yes') is True
    assert load_yaml('!!int 0x10') == 16
    assert load_yaml('!!float 1.5') == 1.5


def test_unsupported_explicit_tag_is_refused() -> None:
    """A tag outside the core schema is a hard error."""
    with pytest.raises(TypeError, match='unsupported YAML tag'):
        _ = load_yaml('!custom value')


def test_null_words_resolve_to_none() -> None:
    """The YAML 1.1 null spellings produce None."""
    assert load_yaml('~') is None
    assert load_yaml('null') is None


def test_float_scalars_resolve() -> None:
    """Plain scalars matching the float grammar become floats."""
    assert load_yaml('1.5') == 1.5
    assert load_yaml('.5') == 0.5


def test_boolean_resolver_refuses_other_words() -> None:
    """An explicitly tagged boolean that is not a YAML word is refused."""
    with pytest.raises(ValueError, match='not a YAML boolean'):
        _ = load_yaml('!!bool maybe')


def test_integer_forms_follow_yaml_1_1() -> None:
    """Binary, hexadecimal, octal, sexagesimal and signed forms resolve."""
    assert load_yaml('0b1010') == 10
    assert load_yaml('0x1f') == 31
    assert load_yaml('010') == 8
    assert load_yaml('1:30') == 90
    assert load_yaml('-1_000') == -1000


def test_float_forms_follow_yaml_1_1() -> None:
    """Underscores, signs, infinities, NaN and sexagesimal forms resolve."""
    assert load_yaml('1_000.5') == 1000.5
    assert load_yaml('-1.5') == -1.5
    assert load_yaml('-.inf') == -math.inf
    assert load_yaml('.inf') == math.inf
    nan = load_yaml('.nan')
    assert isinstance(nan, float)
    assert math.isnan(nan)
    assert load_yaml('1:30.5') == 90.5


def test_empty_stream_is_none() -> None:
    """An empty document holds no value."""
    assert load_yaml('') is None


def test_missing_stream_start_is_refused() -> None:
    """A stream whose first event is not the stream start is malformed."""
    with pytest.raises(TypeError, match='missing YAML stream start'):
        _ = _parse_stream([StreamEndEvent()])


def test_missing_document_start_is_refused() -> None:
    """A stream that starts with a node event is malformed."""
    with pytest.raises(TypeError, match='missing YAML document start'):
        _ = _parse_stream([
            StreamStartEvent(),
            ScalarEvent(None, None, (True, False), 'x')
        ])


def test_unsupported_event_is_refused() -> None:
    """A stream end where a node is expected is malformed."""
    with pytest.raises(TypeError, match='unsupported YAML event'):
        _ = _parse_stream([
            StreamStartEvent(),
            DocumentStartEvent(),
            StreamEndEvent()
        ])


def test_missing_document_end_is_refused() -> None:
    """A document without its end event is malformed."""
    with pytest.raises(TypeError, match='missing YAML document end'):
        _ = _parse_stream([
            StreamStartEvent(),
            DocumentStartEvent(),
            ScalarEvent(None, None, (True, False), 'x'),
            StreamEndEvent(),
        ])


def test_multiple_documents_are_refused() -> None:
    """The reader accepts exactly one document per stream."""
    with pytest.raises(TypeError, match='multiple YAML documents'):
        _ = load_yaml('a\n---\nb\n')


def test_alias_is_refused() -> None:
    """An alias node has no value of its own."""
    with pytest.raises(TypeError, match='YAML aliases are not supported'):
        _ = load_yaml('a: &x 1\nb: *x\n')


def test_non_string_mapping_key_is_refused() -> None:
    """Mapping keys must resolve to strings."""
    with pytest.raises(TypeError, match='unsupported mapping key int'):
        _ = load_yaml('1: value\n')


def test_peek_keeps_a_held_event() -> None:
    """Peeking twice never consumes the event already held."""
    held = ScalarEvent(None, None, (True, False), 'held')
    parser = Parser(iter([]))
    parser.seed(held)
    assert parser.peek() is held
