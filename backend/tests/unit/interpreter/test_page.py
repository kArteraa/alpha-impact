import json
from datetime import UTC, datetime

import pytest

from apps.services.interpreter.planning import PLANS_PATH, load_config
from shared.contracts.errors import DomainError
from shared.contracts.schemas import InterpretRequest, NewsItem, PageContext, Trace
from tests.unit.interpreter.support import Harness, draft_answer

URL = "https://news.example/rate"
PAGE_TEXT = "\n  Ставка снижена до 16% \nЦБ снизил ключевую ставку.\nКредиты подешевеют.\n"


def pasted_news(harness: Harness, **update: object) -> NewsItem:
    return harness.seed.news[0].model_copy(
        update={
            "id": "pasted-news",
            "url": URL,
            "source": "manual",
            "entities": ["product:settlement"],
            **update,
        }
    )


def page_request(harness: Harness, text: str = PAGE_TEXT) -> InterpretRequest:
    return harness.request().model_copy(
        update={"action_context": PageContext(url=URL, text=text, entities=["company:ромашка"])}
    )


def page_draft() -> dict[str, object]:
    answer = draft_answer()
    for block in ("what_happened", "consequences"):
        answer[block] = [{"text": "Ставка снижена", "type": "fact", "source": "news:pasted-news"}]
    for block in ("why_for_you", "actions"):
        answer[block] = [
            {"text": "Компания работает в IT", "type": "fact", "source": "profile:industry_class"}
        ]
    return answer


@pytest.fixture
def page(harness: Harness) -> Harness:
    harness.news.annotate.return_value = pasted_news(harness)
    harness.answers[1] = page_draft()
    return harness


async def test_pasted_page_is_annotated_and_gets_card(page: Harness) -> None:
    response = await page.agent.interpret(page_request(page))
    assert not response.silent
    card = response.cards[0]
    assert card.what_happened[0].source_ref.id == "pasted-news"
    assert card.what_happened[0].source_ref.url == URL
    assert card.bank_view[0].source_ref.id == "logistics-approved"
    page.news.annotate.assert_awaited_once_with(
        "Ставка снижена до 16%", "ЦБ снизил ключевую ставку.\nКредиты подешевеют.", URL
    )
    page.news.search.assert_not_awaited()
    page.counterparties.context.assert_not_awaited()
    trace: Trace = page.traces.save.call_args.args[0]
    page.house_view.claims.assert_any_await(
        subject="trade_logistics", as_of=trace.created_at.date()
    )
    assert any(step.name == "news.annotate" for step in trace.steps if step.step == "tool")
    plan = next(step for step in trace.steps if step.step == "plan")
    assert json.loads(plan.output_summary)["template"]["context"] == [
        "profile",
        "news",
        "house_view",
    ]


async def test_single_line_page_is_title_without_body(page: Harness) -> None:
    await page.agent.interpret(page_request(page, "  Ставка снижена до 16%  "))
    page.news.annotate.assert_awaited_once_with("Ставка снижена до 16%", "", URL)


async def test_irrelevant_page_is_silent_without_llm(harness: Harness) -> None:
    harness.news.annotate.return_value = pasted_news(harness, entities=[], factors=[])
    response = await harness.agent.interpret(page_request(harness))
    assert response.silent
    assert response.silent_reason
    harness.llm.complete.assert_not_awaited()
    harness.house_view.claims.assert_not_awaited()


async def test_old_pasted_news_is_still_assessed(page: Harness) -> None:
    page.news.annotate.return_value = pasted_news(
        page, published_at=datetime(2020, 1, 1, tzinfo=UTC)
    )
    response = await page.agent.interpret(page_request(page))
    assert not response.silent


async def test_page_text_is_not_repeated_in_action_prompt(page: Harness) -> None:
    await page.agent.interpret(page_request(page))
    for call in page.llm.complete.await_args_list:
        if call.kwargs["task"] == "interpret":
            action = json.loads(call.kwargs["user"])["context"]["action"]
            assert action == {"type": "page", "url": URL, "entities": ["company:ромашка"]}


@pytest.mark.parametrize("text", ["", " \n  \n"])
async def test_empty_page_is_a_domain_error_without_annotation(harness: Harness, text: str) -> None:
    with pytest.raises(DomainError):
        await harness.agent.interpret(page_request(harness, text))
    harness.news.annotate.assert_not_awaited()


async def test_long_single_line_is_cut_to_title_and_kept_as_body(page: Harness) -> None:
    limit = load_config(PLANS_PATH).max_title_chars
    text = "Ставка снижена " * limit
    await page.agent.interpret(page_request(page, text))
    page.news.annotate.assert_awaited_once_with(text[:limit].rstrip(), text.strip(), URL)


async def test_headline_only_page_news_is_still_a_fact_source(page: Harness) -> None:
    page.news.annotate.return_value = pasted_news(page, text="")
    response = await page.agent.interpret(page_request(page, "Ставка снижена до 16%"))
    assert response.cards[0].what_happened[0].type.value == "fact"
    assert response.cards[0].what_happened[0].source_ref.id == "pasted-news"
