import html
import re
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime

import httpx

TAG = re.compile(r"<[^>]+>")


class FeedTooLarge(ValueError):
    pass


@dataclass(frozen=True)
class FeedEntry:
    title: str
    text: str
    url: str
    published_at: datetime
    source: str


def plain(value: str | None) -> str:
    return " ".join(html.unescape(TAG.sub(" ", value or "")).split())


def published(value: str | None) -> datetime | None:
    try:
        moment = parsedate_to_datetime(value or "")
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo is not None else None


def source_of(url: str) -> str:
    return httpx.URL(url).host.removeprefix("www.")


def parse_feed(content: bytes, source: str) -> list[FeedEntry]:
    entries = []
    for item in ElementTree.fromstring(content).iter("item"):
        title = plain(item.findtext("title"))
        url = (item.findtext("link") or "").strip()
        moment = published(item.findtext("pubDate"))
        if title and url and moment is not None:
            text = plain(item.findtext("description"))
            entries.append(FeedEntry(title, text, url, moment, source))
    return entries


def build_feed_client(timeout_seconds: float, user_agent: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout_seconds, follow_redirects=True, headers={"User-Agent": user_agent}
    )


async def fetch_feed(client: httpx.AsyncClient, url: str, max_bytes: int) -> list[FeedEntry]:
    content = bytearray()
    async with client.stream("GET", url) as response:
        response.raise_for_status()
        async for chunk in response.aiter_bytes():
            content.extend(chunk)
            if len(content) > max_bytes:
                raise FeedTooLarge(f"feed {url} is larger than {max_bytes} bytes")
    return parse_feed(bytes(content), source_of(url))
