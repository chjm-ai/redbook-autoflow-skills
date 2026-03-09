#!/usr/bin/env python3
"""External trend providers for daily ops planning."""

from __future__ import annotations

from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests

from ops_common import dedupe_and_sort_trends, iso_utc_now, strip_html


def _clean_title(raw_title: str) -> str:
    """Strip source suffixes and noisy separators from RSS titles."""
    title = (raw_title or "").strip()
    title = title.split(" - ")[0].strip()
    title = title.split("_")[0].strip()
    title = title.split("|")[0].strip()
    return title


class TrendProvider:
    """Base interface for trend providers."""

    name = "base"

    def fetch_trends(self, domain: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return normalized trend items."""
        raise NotImplementedError


class GoogleNewsRssProvider(TrendProvider):
    """Fetch recent news headlines from Google News RSS."""

    name = "google-news-rss"
    template = (
        "https://news.google.com/rss/search?q={query}"
        "&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    )

    def fetch_trends(self, domain: str, limit: int = 10) -> list[dict[str, Any]]:
        query = quote_plus(f"{domain} when:1d")
        response = requests.get(self.template.format(query=query), timeout=20)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        trends: list[dict[str, Any]] = []
        channel = root.find("channel")
        if channel is None:
            return trends

        for index, item in enumerate(channel.findall("item"), start=1):
            title = _clean_title(item.findtext("title") or "")
            source_url = (item.findtext("link") or "").strip()
            description = strip_html(item.findtext("description") or "")
            source_name = (item.findtext("source") or "Google News").strip()
            pub_date = item.findtext("pubDate") or ""
            published_at = iso_utc_now()
            if pub_date:
                try:
                    published_at = parsedate_to_datetime(pub_date).astimezone().isoformat(timespec="seconds")
                except (TypeError, ValueError):
                    published_at = iso_utc_now()

            trends.append({
                "trend_id": f"trend_{index:02d}",
                "title": title,
                "summary": description or title,
                "source_url": source_url,
                "published_at": published_at,
                "source_name": source_name,
                "provider": self.name,
            })

        return dedupe_and_sort_trends(trends)[:limit]


PROVIDERS: dict[str, TrendProvider] = {
    GoogleNewsRssProvider.name: GoogleNewsRssProvider(),
}


def get_provider(name: str) -> TrendProvider:
    """Return a configured provider instance by name."""
    try:
        return PROVIDERS[name]
    except KeyError as exc:
        available = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"Unknown provider: {name}. Available: {available}") from exc
