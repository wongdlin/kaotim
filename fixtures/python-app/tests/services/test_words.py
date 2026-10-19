from app.services.words import count_words


def test_ac_1_counts_words_separated_by_whitespace() -> None:
    assert count_words("one two  three") == 3


def test_ec_1_returns_zero_for_blank_input() -> None:
    assert count_words("   ") == 0
