from apps.services.house_view.ingest.config import load_config
from shared.config.factors import FACTORS
from shared.config.house_view_topics import HOUSE_VIEW_SUBJECTS, HOUSE_VIEW_TOPICS, topics_for
from tests.house_view_data import APPROVED


def test_every_approved_subject_is_reachable_by_a_factor() -> None:
    reachable = {topic for factor in FACTORS for topic in topics_for([factor])}
    assert {claim.subject for claim in APPROVED} <= reachable


def test_topics_are_not_factors_and_point_only_to_factors() -> None:
    assert not set(HOUSE_VIEW_TOPICS) & set(FACTORS)
    assert all(factors and set(factors) <= set(FACTORS) for factors in HOUSE_VIEW_TOPICS.values())


def test_key_rate_reaches_inflation_and_debt_market() -> None:
    assert {"key_rate", "inflation", "debt_market"} <= topics_for(["key_rate"])
    assert topics_for([]) == set()


def test_subjects_are_factors_and_topics() -> None:
    assert set(HOUSE_VIEW_SUBJECTS) == set(FACTORS) | set(HOUSE_VIEW_TOPICS)


def test_every_ingest_subject_except_other_is_reachable() -> None:
    assert set(load_config().subjects) - set(HOUSE_VIEW_SUBJECTS) == {"other"}
