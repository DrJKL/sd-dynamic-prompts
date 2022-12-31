import pytest
from unittest import mock
from typing import cast

from pyparsing import ParseException

from prompts.parser.parse import (
    Parser,
    ActionBuilder,
)

from prompts.parser.commands import (
    Command,
    SequenceCommand,
    VariantCommand,
    LiteralCommand,
    WildcardCommand,
)


@pytest.fixture
def wildcard_manager():
    return mock.Mock()


@pytest.fixture
def parser(wildcard_manager) -> Parser:
    return Parser(ActionBuilder(wildcard_manager))


class TestParser:
    def test_basic_parser(self, parser: Parser):
        sequence = parser.parse("hello world")

        assert type(sequence) == SequenceCommand
        assert len(sequence) == 1
        assert type(sequence[0]) == LiteralCommand
        assert sequence[0] == "hello world"

    def test_literal_characters(self, parser: Parser):
        sequence = parser.parse("good-bye world")
        assert len(sequence) == 1
        assert sequence[0] == "good-bye world"

        sequence = parser.parse("good_bye world")
        assert len(sequence) == 1
        assert sequence[0] == "good_bye world"

        sequence = parser.parse("I, love. punctuation")
        assert len(sequence) == 1
        variant = cast(VariantCommand, sequence)
        assert variant[0] == "I, love. punctuation"

    def test_literal_with_accents(self, parser: Parser):
        sequence = parser.parse("Test änderō")
        assert len(sequence) == 1
        assert sequence[0] == "Test änderō"

    def test_wildcard(self, parser: Parser):
        sequence = parser.parse("__colours__")
        assert len(sequence) == 1
        
        wildcard_command = sequence[0]
        assert type(wildcard_command) == WildcardCommand
        wildcard_command = cast(WildcardCommand, wildcard_command)
        assert wildcard_command.wildcard == "colours"

        sequence = parser.parse("__path/to/colours__")
        assert len(sequence) == 1
        
        wildcard_command = sequence[0]
        assert type(wildcard_command) == WildcardCommand
        wildcard_command = cast(WildcardCommand, wildcard_command)
        assert wildcard_command.wildcard == "path/to/colours"

    def test_wildcard_with_accents(self, parser: Parser):
        sequence = parser.parse("__änder__")
        assert len(sequence) == 1
        wildcard_command = cast(WildcardCommand, sequence[0])
        assert wildcard_command.wildcard == "änder"

    def test_weight(self, parser: Parser):
        weight = parser._configure_weight()
        with pytest.raises(ParseException):
            weight.parse_string("1")

        assert weight.parse_string("1::")[0] == 1.0
        assert weight.parse_string("0.25::")[0] == 0.25

    def test_basic_variant(self, parser: Parser):
        sequence = parser.parse("{cat|dog}")

        assert len(sequence) == 1
        assert type(sequence[0]) == VariantCommand

        variant = cast(VariantCommand, sequence[0])
        assert len(variant) == 2
        assert type(variant[0]) == SequenceCommand

        sequence1 = cast(SequenceCommand, variant[0])
        assert len(sequence1) == 1
        assert sequence1[0] == LiteralCommand("cat")

        sequence2 = cast(SequenceCommand, variant[1])
        assert len(sequence2) == 1
        assert sequence2[0] == LiteralCommand("dog")

    def test_variant_with_different_characters(self, parser: Parser):
        sequence = parser.parse("{new york|washing-ton!|änder}")

        variant = cast(VariantCommand, sequence[0])
        assert len(variant) == 3
        assert variant[0][0] == "new york"
        assert variant[1][0] == "washing-ton!"
        assert variant[2][0] == "änder"

    def test_variant_breaks_without_closing_bracket(self, parser: Parser):
        with pytest.raises(ParseException):
            parser.parse("{cat|dog")

    def test_variant_breaks_without_opening_bracket(self, parser: Parser):
        with pytest.raises(ParseException):
            parser.parse("cat|dog}")


    def test_variant_with_wildcard(self, parser: Parser):
        sequence = parser.parse("{__test/colours__|washington}")
        assert len(sequence) == 1
        assert type(sequence[0]) == VariantCommand
        variant = cast(VariantCommand, sequence[0])

        wildcard_command = cast(WildcardCommand, variant[0][0])
        assert wildcard_command.wildcard == "test/colours"
        assert variant[1][0] == "washington"

    def test_variant_sequences(self, parser:Parser):
        sequence = parser.parse("{My favourite colour is __colour__ and not __other_colour__|__colour__ is my favourite colour}")
        assert len(sequence) == 1
        assert type(sequence[0]) == VariantCommand
        variant = cast(VariantCommand, sequence[0])

        assert len(variant) == 2

        sequence1 = variant[0]
        assert len(sequence1) == 4
        assert type(sequence1[0]) == LiteralCommand
        assert sequence1[0] == "My favourite colour is"

        assert type(sequence1[1]) == WildcardCommand
        wildcard_command = cast(WildcardCommand, sequence1[1])
        assert wildcard_command.wildcard == "colour"

        assert type(sequence1[2]) == LiteralCommand
        assert sequence1[2] == "and not"

        assert type(sequence1[3]) == WildcardCommand
        wildcard_command = cast(WildcardCommand, sequence1[3])
        assert wildcard_command.wildcard == "other_colour"

        sequence2 = variant[1]
        assert len(sequence2) == 2

        assert type(sequence2[0]) == WildcardCommand
        wildcard_command = cast(WildcardCommand, sequence2[0])
        assert wildcard_command.wildcard == "colour"

        assert type(sequence2[1]) == LiteralCommand
        assert sequence2[1] == "is my favourite colour"

    def test_variant_with_nested_variant(self, parser: Parser):
        sequence = parser.parse("{__test/colours__|{__test/colours__|washington}}")
        assert len(sequence) == 1
        assert type(sequence[0]) == VariantCommand
        variant = cast(VariantCommand, sequence[0])

        assert len(variant) == 2

        assert type(variant[0][0]) == WildcardCommand
        assert type(variant[1][0]) == VariantCommand

        nested_variant = cast(VariantCommand, variant[1][0])
        assert len(nested_variant) == 2
        assert type(nested_variant[0][0]) == WildcardCommand
        assert nested_variant[0][0].wildcard == "test/colours"

        assert type(nested_variant[1][0]) == LiteralCommand
        assert nested_variant[1][0] == "washington"

    def test_variant_with_weights(self, parser: Parser):
        sequence = parser.parse("{1::cat|2::dog|3::bird} test")

        variant = cast(VariantCommand, sequence[0])
        assert variant.weights[0] == 1
        assert variant.weights[1] == 2
        assert variant.weights[2] == 3

        assert variant[0][0] == "cat"
        assert variant[1][0] == "dog"
        assert variant[2][0] == "bird"

    def test_variant_with_defaultweights(self, parser: Parser):
        sequence = parser.parse("{1::cat|dog|3::bird} test")

        variant = cast(VariantCommand, sequence[0])
        assert variant.weights[0] == 1
        assert variant.weights[1] == 1
        assert variant.weights[2] == 3

    def test_range(self, parser: Parser):
        sequence = parser.parse("{2$$cat|dog|bird}")
        variant = cast(VariantCommand, sequence[0])

        assert variant.min_bound == 2
        assert variant.max_bound == 2
        assert variant.sep == ","

        sequence = parser.parse("{1-2$$cat|dog|bird}")
        variant = cast(VariantCommand, sequence[0])

        assert variant.min_bound == 1
        assert variant.max_bound == 2

        sequence = parser.parse("{1-$$cat|dog|bird}")
        variant = cast(VariantCommand, sequence[0])

        assert variant.min_bound == 1
        assert variant.max_bound == 3

        sequence = parser.parse("{-2$$cat|dog|bird}")
        variant = cast(VariantCommand, sequence[0])

        assert variant.min_bound == 1
        assert variant.max_bound == 2

        sequence = parser.parse("{2$$ and $$cat|dog|bird}")
        variant = cast(VariantCommand, sequence[0])

        assert variant.min_bound == 2
        assert variant.max_bound == 2
        assert variant.sep == " and "

    def test_prompt_editing(self, parser: Parser):
        prompt_editing = parser._configure_prompt_editing()
        assert prompt_editing.parse_string("[start prompt|end prompt]")[0] == "[start prompt|end prompt]"
        with pytest.raises(ParseException):
            prompt_editing.parse_string("[start prompt|end prompt")

        sequence = parser.parse("[start prompt|end prompt]")
        assert len(sequence) == 1

        assert type(sequence[0]) == LiteralCommand
        assert sequence[0] == "[start prompt|end prompt]"

        sequence = parser.parse("{option1|[start prompt|end prompt]}")
        assert len(sequence) == 1
        assert type(sequence[0]) == VariantCommand
        variant = cast(VariantCommand, sequence[0])

        assert len(variant) == 2
        assert type(variant[0][0]) == LiteralCommand
        assert variant[0][0] == "option1"

        assert type(variant[1][0] == LiteralCommand)
        assert variant[1][0] == "[start prompt|end prompt]"

        
    def test_comments(self, parser: Parser):
        prompt = """
        one
        two
        three // comment
        # A comment
        four /* another comment */
        // another comment
        five
        {cat|/*some comment */dog|bird}
        """

        sequence = parser.parse(prompt)
        assert len(sequence) == 2
        assert sequence[0] == "one two three four five"
        variant = cast(VariantCommand, sequence[1])
        assert len(variant) == 3
        assert variant[0][0] == "cat"
        assert variant[1][0] == "dog"
        assert variant[2][0] == "bird"