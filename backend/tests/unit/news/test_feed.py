from datetime import UTC, datetime, timedelta, timezone

import httpx
import pytest

from apps.services.news.feed import FeedTooLarge, fetch_feed, parse_feed, source_of
from tests.news_data import NOW, item, rss

MOSCOW = timezone(timedelta(hours=3))
KOMMERSANT = (
    "﻿"
    '<?xml version="1.0" encoding="utf-8"?>'
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
    "<title>Коммерсантъ</title><item>"
    "<guid>https://www.kommersant.ru/doc/1</guid><category>Экономика</category>"
    "<title>ЦБ снизил ключевую ставку до 16%</title>"
    "<link>https://www.kommersant.ru/doc/1</link>"
    "<pubDate>Wed, 21 Oct 2026 12:38:07 +0300</pubDate>"
    "<description>Банк России &lt;b&gt;снизил&lt;/b&gt; ставку &amp;laquo;до 16%&amp;raquo;."
    "</description></item></channel></rss>"
).encode()
TASS = (
    '<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel><title>ТАСС</title>'
    "<item><title>Курс юаня вырос</title>"
    "<link><![CDATA[https://tass.ru/ekonomika/1]]></link>"
    "<pubDate>Wed, 21 Oct 2026 17:01:43 +0300</pubDate>"
    "<description><![CDATA[<p>Юань подорожал</p>]]></description></item></channel></rss>"
).encode()


def test_kommersant_item_becomes_plain_entry() -> None:
    [entry] = parse_feed(KOMMERSANT, "kommersant.ru")

    assert entry.title == "ЦБ снизил ключевую ставку до 16%"
    assert entry.text == "Банк России снизил ставку «до 16%»."
    assert entry.url == "https://www.kommersant.ru/doc/1"
    assert entry.published_at == datetime(2026, 10, 21, 12, 38, 7, tzinfo=MOSCOW)
    assert entry.source == "kommersant.ru"


def test_cdata_link_and_html_description_are_read() -> None:
    [entry] = parse_feed(TASS, "tass.ru")

    assert entry.url == "https://tass.ru/ekonomika/1"
    assert entry.text == "Юань подорожал"


def test_escaped_tags_are_unescaped_and_removed() -> None:
    description = "&amp;lt;p&amp;gt;Юань &amp;lt;b&amp;gt;подорожал&amp;lt;/b&amp;gt;"
    content = rss(item("Курс", "https://tass.ru/1", NOW, description))

    [entry] = parse_feed(content, "tass.ru")

    assert entry.text == "Юань подорожал"


def test_literal_angle_brackets_keep_the_text_between_them() -> None:
    content = rss(item("Курс", "https://tass.ru/1", NOW, "Ставка &amp;lt; 16%, курс &amp;gt; 90"))

    [entry] = parse_feed(content, "tass.ru")

    assert entry.text == "Ставка < 16%, курс > 90"


def test_item_without_description_has_empty_text() -> None:
    content = rss(item("Только заголовок", "https://www.vedomosti.ru/1", NOW))

    [entry] = parse_feed(content, "vedomosti.ru")

    assert entry.text == ""


def test_items_without_title_link_or_valid_date_are_skipped() -> None:
    content = rss(
        item("", "https://a.example/1", NOW),
        item("Без ссылки", "", NOW),
        "<item><title>Без даты</title><link>https://a.example/3</link></item>",
        "<item><title>Кривая дата</title><link>https://a.example/4</link>"
        "<pubDate>вчера</pubDate></item>",
        "<item><title>Без пояса</title><link>https://a.example/5</link>"
        "<pubDate>Wed, 21 Oct 2026 12:00:00 -0000</pubDate></item>",
        item("Годная", "https://a.example/6", NOW),
    )

    assert [entry.title for entry in parse_feed(content, "a.example")] == ["Годная"]


def test_source_is_host_without_www() -> None:
    assert source_of("https://www.kommersant.ru/RSS/section-business.xml") == "kommersant.ru"
    assert source_of("https://tass.ru/rss/v2.xml") == "tass.ru"


def serve(content: bytes, status: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=content)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_fetch_reads_feed_and_names_source_by_url() -> None:
    async with serve(KOMMERSANT) as client:
        entries = await fetch_feed(client, "https://www.kommersant.ru/RSS/news.xml", 1_000_000)

    assert [(entry.source, entry.published_at.astimezone(UTC)) for entry in entries] == [
        ("kommersant.ru", datetime(2026, 10, 21, 9, 38, 7, tzinfo=UTC))
    ]


async def test_feed_over_size_limit_is_rejected() -> None:
    async with serve(KOMMERSANT) as client:
        with pytest.raises(FeedTooLarge):
            await fetch_feed(client, "https://www.kommersant.ru/RSS/news.xml", 100)


async def test_http_error_is_raised() -> None:
    async with serve(b"", status=503) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_feed(client, "https://www.kommersant.ru/RSS/news.xml", 1_000_000)
