#!/usr/bin/env python3
"""Collect vertical news trends into an ops plan directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ops_common import dedupe_and_sort_trends, get_plan_dir, write_json, write_markdown
from trend_providers import get_provider


def render_trends_markdown(domain: str, provider_name: str, trends: list[dict]) -> str:
    """Render trend briefs as Markdown."""
    lines = [
        "# 热点摘要",
        "",
        f"- 垂类: {domain}",
        f"- 来源 provider: {provider_name}",
        f"- 热点数量: {len(trends)}",
        "",
        "## 条目",
        "",
    ]
    for index, trend in enumerate(trends, start=1):
        lines.extend([
            f"{index}. {trend['title']}",
            f"   - 来源: {trend['source_name']}",
            f"   - 发布时间: {trend['published_at']}",
            f"   - 链接: {trend['source_url']}",
            f"   - 摘要: {trend['summary']}",
        ])
    return "\n".join(lines)


def collect_trends(
    account: str,
    domain: str,
    provider_name: str = "google-news-rss",
    limit: int = 10,
    plan_id: str | None = None,
    raw_payload: dict | None = None,
) -> dict:
    """Collect and persist normalized external trend briefs."""
    resolved_plan_id, plan_dir = get_plan_dir(account=account, domain=domain, explicit_plan_id=plan_id)
    plan_dir.mkdir(parents=True, exist_ok=True)

    if raw_payload is None:
        provider = get_provider(provider_name)
        trends = provider.fetch_trends(domain=domain, limit=limit)
    else:
        provider_name = raw_payload.get("provider", provider_name)
        trends = dedupe_and_sort_trends(raw_payload.get("trends", []))[:limit]

    payload = {
        "plan_id": resolved_plan_id,
        "account": account,
        "domain": domain,
        "provider": provider_name,
        "count": len(trends),
        "trends": trends,
    }
    write_json(plan_dir / "trend_briefs.json", payload)
    write_markdown(plan_dir / "trend_briefs.md", render_trends_markdown(domain, provider_name, trends))
    return {
        "plan_id": resolved_plan_id,
        "plan_dir": str(plan_dir),
        "trends": trends,
        "provider": provider_name,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect vertical news trends into an ops plan directory.")
    parser.add_argument("--account", required=True, help="Target account name")
    parser.add_argument("--domain", required=True, help="Vertical domain label, e.g. AI 工具")
    parser.add_argument("--provider", default="google-news-rss", help="Trend provider name")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--plan-id", default=None)
    parser.add_argument("--raw-file", default=None, help="Optional JSON file with provider output")
    args = parser.parse_args()

    raw_payload = None
    if args.raw_file:
        raw_payload = json.loads(Path(args.raw_file).read_text(encoding="utf-8"))

    result = collect_trends(
        account=args.account,
        domain=args.domain,
        provider_name=args.provider,
        limit=args.limit,
        plan_id=args.plan_id,
        raw_payload=raw_payload,
    )
    print(result["plan_dir"])


if __name__ == "__main__":
    main()
