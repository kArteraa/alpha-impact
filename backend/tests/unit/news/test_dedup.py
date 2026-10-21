from apps.services.news.dedup import is_duplicate, numbers

THRESHOLD = 0.93


def test_different_rates_give_different_numbers() -> None:
    assert numbers("ЦБ снизил ставку до 16%") != numbers("ЦБ снизил ставку до 17%")


def test_paraphrase_with_same_rate_gives_same_numbers() -> None:
    assert numbers("ЦБ снизил ставку до 16%") == numbers("Банк России понизил ставку до 16%")


def test_thousand_separators_and_decimal_comma_are_normalized() -> None:
    assert numbers("выпуск на 1 200,5 млрд") == numbers("выпуск на 1200.5 млрд")
    assert numbers("выпуск на 1 200 млрд") == numbers("выпуск на 1200 млрд")


def test_month_is_part_of_the_date() -> None:
    assert numbers("заседание 24 июля") != numbers("заседание 24 августа")
    assert numbers("с 1 мая") == numbers("на 1 Май")


def test_words_starting_like_months_are_not_dates() -> None:
    assert numbers("маркетплейс, маяк, Мартынов и мартовский") == numbers("")
    assert numbers("в марте и в мае") == numbers("март, май")


def test_same_value_written_differently_is_the_same_number() -> None:
    assert numbers("ставка 16%") == numbers("ставка 16,0%")
    assert numbers("выпуск на 1000 млн") != numbers("выпуск на 1 млрд")


def test_duplicate_needs_close_vectors_and_same_numbers() -> None:
    same = numbers("MOL выкупит долю за 1 млрд")
    other = numbers("MOL выкупит долю за 2 млрд")

    assert is_duplicate(0.95, same, same, THRESHOLD)
    assert not is_duplicate(0.95, same, other, THRESHOLD)
    assert not is_duplicate(0.9, same, same, THRESHOLD)
