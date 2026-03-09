#!/usr/bin/env python3
"""Shared helpers for daily ops planning scripts."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import UTC, date, datetime
from html import unescape
from pathlib import Path
from typing import Any


OPS_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = OPS_ROOT.parent
AUTO_FLOW_ROOT = SKILLS_ROOT / "redbook-auto-flow"
OPS_DATASET_ROOT = AUTO_FLOW_ROOT / "data-sources" / "ops"
WORKSPACE_ROOT = AUTO_FLOW_ROOT / "workspace"

CONTENT_DATA_MARKER = "CONTENT_DATA_RESULT:"

CSV_COLUMNS = [
    "note_id",
    "title",
    "posted_at",
    "impressions",
    "views",
    "cover_click_rate",
    "likes",
    "comments",
    "favorites",
    "new_followers",
    "shares",
    "avg_view_seconds",
    "danmaku",
    "planning_score",
]

TITLE_PATTERN_RULES = {
    "教程": ("教程", "指南", "步骤", "保姆级", "手把手", "入门", "配置"),
    "清单": ("清单", "合集", "汇总", "盘点", "推荐", "模板"),
    "实测": ("实测", "测评", "对比", "横评", "体验", "试用", "踩坑"),
    "案例": ("案例", "复盘", "拆解", "方法论", "经验", "项目"),
    "热点": ("热点", "新闻", "发布", "更新", "趋势"),
}

STOP_TERMS = {
    "一个",
    "一些",
    "这个",
    "那个",
    "今天",
    "最新",
    "真的",
    "如何",
    "什么",
    "为什么",
    "可以",
    "我们",
    "他们",
    "你们",
    "自己",
    "进行",
    "已经",
    "相关",
    "行业",
    "垂类",
    "凤凰网",
    "搜狐网",
    "中华网",
    "网易网",
    "同花顺财经",
    "手机鳳凰網",
    "手机网易网",
    "要来了",
}

BAD_TERM_FRAGMENTS = (
    "所有",
    "这些",
    "那些",
    "工作",
    "了解",
    "咨询",
    "一天",
    "可以",
    "替代",
    "把人",
    "手机",
    "财经",
    "准确率",
)


def slugify(value: str) -> str:
    """Convert user text into a filesystem-safe slug."""
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", lowered)
    lowered = lowered.strip("-")
    if lowered:
        return lowered
    fallback = re.sub(r"\s+", "-", value.strip())
    return fallback.strip("-") or "default"


def build_plan_id(account: str, domain: str, explicit_plan_id: str | None = None) -> str:
    """Build a deterministic daily ops plan id."""
    if explicit_plan_id:
        return explicit_plan_id.strip()
    day = date.today().strftime("%Y%m%d")
    return f"ops_{slugify(account)}_{slugify(domain)}_{day}"


def get_plan_dir(account: str, domain: str, explicit_plan_id: str | None = None) -> tuple[str, Path]:
    """Return the resolved plan id and directory path."""
    plan_id = build_plan_id(account=account, domain=domain, explicit_plan_id=explicit_plan_id)
    return plan_id, OPS_DATASET_ROOT / plan_id


def write_json(path: Path, payload: Any) -> None:
    """Write pretty JSON to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    """Read JSON from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_markdown(path: Path, content: str) -> None:
    """Write Markdown to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def extract_json_after_marker(raw_text: str, marker: str) -> dict[str, Any]:
    """Parse the first JSON object following a CLI marker."""
    marker_index = raw_text.find(marker)
    if marker_index == -1:
        raise ValueError(f"{marker} marker not found")
    json_text = raw_text[marker_index + len(marker):].strip()
    payload = json.loads(json_text)
    if not isinstance(payload, dict):
        raise ValueError(f"{marker} payload must be an object")
    return payload


def strip_html(value: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    text = unescape(re.sub(r"<[^>]+>", " ", value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_numeric(value: Any) -> float | None:
    """Parse numbers represented as strings, dashes, or percentages."""
    if value in (None, "", "-"):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return None
    percent = text.endswith("%")
    if percent:
        text = text[:-1]
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    number = float(match.group(0))
    return number / 100 if percent else number


def compute_planning_score(row: dict[str, Any]) -> float:
    """Compute a lightweight score for ranking recent content."""
    return round(
        (row.get("favorites") or 0) * 2.0
        + (row.get("likes") or 0) * 1.2
        + (row.get("comments") or 0) * 1.6
        + (row.get("shares") or 0) * 1.5
        + (row.get("new_followers") or 0) * 4.0
        + (row.get("views") or 0) * 0.02,
        2,
    )


def normalize_content_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize content-data rows into a stable schema."""
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized = {
            "note_id": row.get("_id") or "",
            "title": (row.get("标题") or "").strip(),
            "posted_at": row.get("发布时间") or "-",
            "impressions": parse_numeric(row.get("曝光")),
            "views": parse_numeric(row.get("观看")),
            "cover_click_rate": parse_numeric(row.get("封面点击率")),
            "likes": parse_numeric(row.get("点赞")),
            "comments": parse_numeric(row.get("评论")),
            "favorites": parse_numeric(row.get("收藏")),
            "new_followers": parse_numeric(row.get("涨粉")),
            "shares": parse_numeric(row.get("分享")),
            "avg_view_seconds": parse_numeric(row.get("人均观看时长")),
            "danmaku": parse_numeric(row.get("弹幕")),
        }
        normalized["planning_score"] = compute_planning_score(normalized)
        normalized_rows.append(normalized)

    normalized_rows.sort(key=lambda item: item["planning_score"], reverse=True)
    return normalized_rows


def infer_top_patterns(rows: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    """Infer which content patterns perform best for the account."""
    scores: Counter[str] = Counter()
    examples: dict[str, list[str]] = {pattern: [] for pattern in TITLE_PATTERN_RULES}

    for row in rows[:10]:
        title = row.get("title") or ""
        planning_score = row.get("planning_score") or 0
        for pattern, keywords in TITLE_PATTERN_RULES.items():
            if any(keyword.lower() in title.lower() for keyword in keywords):
                scores[pattern] += int(planning_score)
                if len(examples[pattern]) < 2:
                    examples[pattern].append(title)

    ranked = []
    for pattern, score in scores.most_common(limit):
        ranked.append({
            "pattern": pattern,
            "score": score,
            "examples": examples.get(pattern, []),
        })
    if ranked:
        return ranked
    return [{
        "pattern": "教程",
        "score": 0,
        "examples": [row.get("title", "") for row in rows[:2] if row.get("title")],
    }]


def normalize_content_snapshot(
    payload: dict[str, Any],
    account: str,
    domain: str,
    plan_id: str,
    collected_at: str | None = None,
) -> dict[str, Any]:
    """Normalize content-data payload into the ops snapshot schema."""
    collected_at = collected_at or datetime.now().isoformat(timespec="seconds")
    normalized_rows = normalize_content_rows(payload.get("rows", []))
    top_patterns = infer_top_patterns(normalized_rows)
    return {
        "plan_id": plan_id,
        "account": account,
        "domain": domain,
        "collected_at": collected_at,
        "requested_page_num": payload.get("requested_page_num"),
        "requested_page_size": payload.get("requested_page_size"),
        "requested_type": payload.get("requested_type"),
        "resolved_page_num": payload.get("resolved_page_num"),
        "resolved_page_size": payload.get("resolved_page_size"),
        "resolved_type": payload.get("resolved_type"),
        "request_url": payload.get("request_url"),
        "total": payload.get("total"),
        "count_returned": payload.get("count_returned"),
        "top_patterns": top_patterns,
        "rows": normalized_rows,
        "raw_payload": payload,
    }


def write_snapshot_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write normalized content snapshot rows to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in CSV_COLUMNS})


def dedupe_and_sort_trends(trends: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate trend items and sort them by published time descending."""
    by_key: dict[str, dict[str, Any]] = {}
    for trend in trends:
        url = (trend.get("source_url") or "").strip()
        title = (trend.get("title") or "").strip()
        if not title:
            continue
        key = url or re.sub(r"\s+", " ", title).lower()
        existing = by_key.get(key)
        if not existing:
            by_key[key] = trend
            continue
        if trend.get("published_at", "") > existing.get("published_at", ""):
            by_key[key] = trend
    return sorted(by_key.values(), key=lambda item: item.get("published_at", ""), reverse=True)


def _normalize_candidate_term(term: str) -> str:
    term = re.sub(r"[^\w\u4e00-\u9fff\-\+\.\s]", " ", term)
    term = re.sub(r"\s+", " ", term).strip()
    return term


def extract_candidate_terms(text: str, domain: str, limit: int = 4) -> list[str]:
    """Extract a few search-friendly terms from trend text."""
    candidates: list[str] = []
    normalized_text = text.replace(domain, f" {domain} ")

    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-\+\.]{1,30}", normalized_text):
        term = _normalize_candidate_term(raw)
        if len(term) >= 2:
            candidates.append(term)

    for raw in re.findall(r"[\u4e00-\u9fff]{2,16}", normalized_text):
        term = _normalize_candidate_term(raw)
        if term and term not in STOP_TERMS:
            candidates.append(term)

    results: list[str] = []
    seen: set[str] = set()
    domain_lower = domain.lower()
    for candidate in candidates:
        key = candidate.lower()
        if key in seen:
            continue
        if candidate in STOP_TERMS:
            continue
        if any(fragment in candidate for fragment in BAD_TERM_FRAGMENTS):
            continue
        if re.fullmatch(r"[\d\.]+", candidate):
            continue
        if len(candidate) <= 2 and candidate.lower() != domain_lower:
            continue
        if len(candidate) > 12:
            continue
        seen.add(key)
        if domain_lower not in key and domain not in candidate:
            candidate = f"{domain} {candidate}"
        results.append(candidate)
        if len(results) >= limit:
            break
    return results or [domain]


def summarize_account_snapshot(snapshot: dict[str, Any]) -> list[str]:
    """Build a short human-readable summary for the account snapshot."""
    rows = snapshot.get("rows", [])
    top_patterns = snapshot.get("top_patterns", [])
    highlights = []
    if rows:
        top_row = rows[0]
        highlights.append(
            f"近期表现最好的笔记是《{top_row.get('title', '-')}》，规划分 {top_row.get('planning_score', 0)}。"
        )
    if top_patterns:
        patterns_text = "、".join(item["pattern"] for item in top_patterns[:3])
        highlights.append(f"账号近期更适合继续放大这几类表达：{patterns_text}。")
    return highlights


def iso_utc_now() -> str:
    """Return a stable UTC timestamp."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()
