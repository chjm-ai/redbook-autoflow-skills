#!/usr/bin/env python3
"""Build the daily ops plan from account snapshot and trend briefs."""

from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any

from ops_common import (
    get_plan_dir,
    extract_candidate_terms,
    read_json,
    summarize_account_snapshot,
    write_json,
    write_markdown,
)


def _build_reason(pattern: str, trend_title: str) -> str:
    return f"来自热点《{trend_title}》，并且账号近期更适合用{pattern}型表达承接。"


def _keyword_quality_score(keyword: str, domain: str) -> int:
    """Score whether a keyword looks like a usable platform query."""
    score = 0
    keyword = keyword.strip()
    if keyword == domain:
        return 60
    if len(keyword) <= len(domain) + 8:
        score += 25
    if len(keyword.split()) <= 3:
        score += 12
    if all(fragment not in keyword for fragment in ("所有", "这些", "工作", "了解", "咨询", "手机", "财经")):
        score += 18
    if any(token in keyword.lower() for token in ("ai", "agent", "工具", "助手", "自动化", "教程", "工作流", "搜索")):
        score += 16
    return score


def _is_search_ready_keyword(keyword: str, domain: str) -> bool:
    """Return whether a keyword is safe to use as the primary platform query."""
    remaining = keyword.replace(domain, "", 1).strip()
    if not remaining:
        return False
    if len(remaining) > 8:
        return False
    if any(fragment in remaining for fragment in ("所有", "工作", "了解", "咨询", "班级", "手机", "财经", "这些", "那些")):
        return False
    if any(char.isdigit() for char in remaining):
        return False
    if any(token in remaining.lower() for token in ("agent", "工具", "助手", "自动化", "教程", "工作流", "搜索", "写作", "配图", "发布", "提示词")):
        return True
    if any(token in remaining for token in ("智能体", "教程", "工作流", "搜索", "写作", "配图", "发布", "提示词", "模型", "助手")):
        return True
    return False


def generate_daily_keywords(
    snapshot: dict[str, Any],
    trend_payload: dict[str, Any],
    keyword_limit: int = 10,
) -> dict[str, Any]:
    """Generate ranked keywords from account signals and current trends."""
    domain = snapshot["domain"]
    top_patterns = snapshot.get("top_patterns", [])
    lead_pattern = top_patterns[0]["pattern"] if top_patterns else "教程"
    keywords: "OrderedDict[str, dict[str, Any]]" = OrderedDict()

    def upsert_keyword(keyword: str, reason: str, trend_id: str | None, score: float) -> None:
        entry = keywords.get(keyword)
        adjusted_score = score + _keyword_quality_score(keyword, domain)
        if entry is None:
            entry = {
                "keyword": keyword,
                "reason": reason,
                "related_trend_ids": [],
                "score": adjusted_score,
            }
            keywords[keyword] = entry
        else:
            if adjusted_score > entry["score"]:
                entry["score"] = adjusted_score
                entry["reason"] = reason
        if trend_id and trend_id not in entry["related_trend_ids"]:
            entry["related_trend_ids"].append(trend_id)

    upsert_keyword(
        keyword=domain,
        reason=f"保留垂类主词，避免当天关键词完全偏离账号主线。建议用{lead_pattern}型内容承接。",
        trend_id=None,
        score=55,
    )

    trends = trend_payload.get("trends", [])
    for index, trend in enumerate(trends):
        terms = extract_candidate_terms(
            text=f"{trend.get('title', '')} {trend.get('summary', '')}",
            domain=domain,
            limit=4,
        )
        base_score = max(100 - index * 7, 55)
        for term_index, term in enumerate(terms):
            upsert_keyword(
                keyword=term,
                reason=_build_reason(lead_pattern, trend.get("title", "")),
                trend_id=trend.get("trend_id"),
                score=base_score - term_index * 3,
            )

    upsert_keyword(
        keyword=f"{domain} {lead_pattern}",
        reason=f"账号最近该类型内容表现更稳，可作为热点词不足时的兜底搜索词。",
        trend_id=None,
        score=62,
    )

    ranked = sorted(keywords.values(), key=lambda item: item["score"], reverse=True)[:keyword_limit]
    selected_keyword = f"{domain} {lead_pattern}"
    for item in ranked:
        if _is_search_ready_keyword(item["keyword"], domain):
            selected_keyword = item["keyword"]
            break
    return {
        "domain": domain,
        "lead_pattern": lead_pattern,
        "selected_keyword": selected_keyword,
        "keywords": ranked,
    }


def render_planning_summary(
    snapshot: dict[str, Any],
    trend_payload: dict[str, Any],
    keyword_payload: dict[str, Any],
) -> str:
    """Render the daily plan summary in Markdown."""
    lines = [
        "# 每日运营规划",
        "",
        f"- 账号: {snapshot['account']}",
        f"- 垂类: {snapshot['domain']}",
        f"- 计划时间: {datetime.now().isoformat(timespec='seconds')}",
        f"- 今日主推关键词: {keyword_payload['selected_keyword']}",
        "",
        "## 账号侧观察",
        "",
    ]
    for item in summarize_account_snapshot(snapshot):
        lines.append(f"- {item}")

    lines.extend([
        "",
        "## 今日热点",
        "",
    ])
    for trend in trend_payload.get("trends", [])[:5]:
        lines.append(f"- {trend['title']} ({trend['source_name']})")

    lines.extend([
        "",
        "## 推荐搜索词",
        "",
    ])
    for entry in keyword_payload["keywords"]:
        lines.append(f"- {entry['keyword']}：{entry['reason']}")

    lines.extend([
        "",
        "## 执行建议",
        "",
        f"- 先用 `{keyword_payload['selected_keyword']}` 跑小红书站内搜索，再进入现有 writer / illustrator / publish 链路。",
        "- 发布动作默认保留人工确认，不直接自动点发布。",
    ])
    return "\n".join(lines)


def build_daily_plan(
    account: str,
    domain: str,
    plan_id: str | None = None,
    keyword_limit: int = 10,
) -> dict[str, Any]:
    """Read collected inputs and build the final daily ops plan."""
    resolved_plan_id, plan_dir = get_plan_dir(account=account, domain=domain, explicit_plan_id=plan_id)
    snapshot = read_json(plan_dir / "account_snapshot.json")
    trend_payload = read_json(plan_dir / "trend_briefs.json")

    keyword_payload = generate_daily_keywords(
        snapshot=snapshot,
        trend_payload=trend_payload,
        keyword_limit=keyword_limit,
    )
    daily_keywords = {
        "plan_id": resolved_plan_id,
        "account": account,
        "domain": domain,
        "planned_at": datetime.now().isoformat(timespec="seconds"),
        **keyword_payload,
    }
    summary_md = render_planning_summary(snapshot, trend_payload, daily_keywords)

    write_json(plan_dir / "daily_keywords.json", daily_keywords)
    write_markdown(plan_dir / "planning_summary.md", summary_md)
    write_json(
        plan_dir / "manifest.json",
        {
            "plan_id": resolved_plan_id,
            "account": account,
            "domain": domain,
            "planned_at": daily_keywords["planned_at"],
            "selected_keyword": daily_keywords["selected_keyword"],
            "files": {
                "account_snapshot": "account_snapshot.json",
                "account_snapshot_csv": "account_snapshot.csv",
                "trend_briefs": "trend_briefs.json",
                "trend_briefs_md": "trend_briefs.md",
                "daily_keywords": "daily_keywords.json",
                "planning_summary": "planning_summary.md",
            },
        },
    )
    return {
        "plan_id": resolved_plan_id,
        "plan_dir": str(plan_dir),
        "selected_keyword": daily_keywords["selected_keyword"],
        "daily_keywords": daily_keywords,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the daily ops plan from collected snapshot and trends.")
    parser.add_argument("--account", required=True, help="Target account name")
    parser.add_argument("--domain", required=True, help="Vertical domain label, e.g. AI 工具")
    parser.add_argument("--plan-id", default=None)
    parser.add_argument("--keyword-limit", type=int, default=10)
    args = parser.parse_args()

    result = build_daily_plan(
        account=args.account,
        domain=args.domain,
        plan_id=args.plan_id,
        keyword_limit=args.keyword_limit,
    )
    print(Path(result["plan_dir"]) / "manifest.json")


if __name__ == "__main__":
    main()
