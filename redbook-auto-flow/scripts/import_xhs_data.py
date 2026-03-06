#!/usr/bin/env python3
"""Import xhs_note rows from MediaCrawlerPro SQLite into shared data-sources."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path


AUTO_FLOW_ROOT = Path(__file__).resolve().parent.parent
DATASET_ROOT = AUTO_FLOW_ROOT / "data-sources" / "xhs"


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "all"


def _build_dataset_id(keyword: str, explicit_dataset_id: str | None) -> str:
    if explicit_dataset_id:
        return explicit_dataset_id.strip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"xhs_{_slugify(keyword)}_{timestamp}"


def _parse_int(value) -> int:
    if value is None:
        return 0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _format_ts(value) -> str:
    try:
        return datetime.fromtimestamp(int(value) / 1000).isoformat(timespec="seconds")
    except Exception:
        return ""


def _query_notes(db_path: Path, keyword: str, limit: int):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
              id,
              note_id,
              title,
              desc,
              nickname,
              liked_count,
              collected_count,
              comment_count,
              share_count,
              note_url,
              source_keyword,
              tag_list,
              image_list,
              time
            FROM xhs_note
            WHERE (? = '' OR source_keyword LIKE '%' || ? || '%')
            ORDER BY time DESC
            LIMIT ?
            """,
            (keyword, keyword, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _build_summary(notes: list[dict], keyword: str, dataset_id: str) -> str:
    total = len(notes)
    if not notes:
        return "\n".join(
            [
                "# 数据摘要",
                "",
                f"- 数据集: {dataset_id}",
                f"- 查询关键词: {keyword or '全部'}",
                "- 笔记数: 0",
                "",
                "未查询到可用数据。",
            ]
        ) + "\n"

    for note in notes:
        note["liked_count_num"] = _parse_int(note.get("liked_count"))
        note["collected_count_num"] = _parse_int(note.get("collected_count"))
        note["comment_count_num"] = _parse_int(note.get("comment_count"))
        note["share_count_num"] = _parse_int(note.get("share_count"))
        note["time_iso"] = _format_ts(note.get("time"))

    top_liked = sorted(notes, key=lambda x: x["liked_count_num"], reverse=True)[:10]
    author_counter = Counter(note.get("nickname") or "unknown" for note in notes)
    keyword_counter = Counter(note.get("source_keyword") or "unknown" for note in notes)

    lines = [
        "# 数据摘要",
        "",
        f"- 数据集: {dataset_id}",
        f"- 查询关键词: {keyword or '全部'}",
        f"- 笔记总数: {total}",
        f"- 平均点赞: {sum(n['liked_count_num'] for n in notes) // total}",
        f"- 平均收藏: {sum(n['collected_count_num'] for n in notes) // total}",
        f"- 平均评论: {sum(n['comment_count_num'] for n in notes) // total}",
        "",
        "## 热门笔记 Top 10（按点赞）",
        "",
    ]
    for idx, note in enumerate(top_liked, start=1):
        lines.extend(
            [
                f"{idx}. {note.get('title') or '无标题'}",
                f"   - 作者: {note.get('nickname') or '未知'}",
                f"   - 点赞/收藏/评论/分享: {note['liked_count_num']}/{note['collected_count_num']}/{note['comment_count_num']}/{note['share_count_num']}",
                f"   - 关键词: {note.get('source_keyword') or ''}",
                f"   - 时间: {note.get('time_iso') or ''}",
                f"   - 链接: {note.get('note_url') or ''}",
            ]
        )

    lines.extend(["", "## 高频作者", ""])
    for author, count in author_counter.most_common(10):
        lines.append(f"- {author}: {count}")

    lines.extend(["", "## 关键词分布", ""])
    for source_keyword, count in keyword_counter.most_common(10):
        lines.append(f"- {source_keyword}: {count}")

    lines.extend(
        [
            "",
            "## Writer 使用建议",
            "",
            "- 先读热门笔记标题，提炼选题角度和标题句式。",
            "- 结合点赞/收藏高的样本，优先选择高收藏价值的内容结构。",
            "- 同一份数据可以支持多个选题和多篇候选文案，不要只写一篇。",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_csv(path: Path, notes: list[dict]):
    fieldnames = [
        "id",
        "note_id",
        "title",
        "desc",
        "nickname",
        "liked_count",
        "collected_count",
        "comment_count",
        "share_count",
        "note_url",
        "source_keyword",
        "tag_list",
        "image_list",
        "time",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for note in notes:
            writer.writerow({key: note.get(key, "") for key in fieldnames})


def main():
    parser = argparse.ArgumentParser(
        description="Import xhs_note rows into shared redbook-auto-flow data-sources."
    )
    parser.add_argument("--db-path", required=True, help="Path to media_crawler.db")
    parser.add_argument("--keyword", default="", help="source_keyword filter")
    parser.add_argument("--limit", type=int, default=50, help="Max note rows to import")
    parser.add_argument("--dataset-id", default=None, help="Explicit dataset_id to create")
    args = parser.parse_args()

    db_path_input = args.db_path
    db_path = Path(args.db_path).expanduser().resolve()
    dataset_id = _build_dataset_id(args.keyword, args.dataset_id)
    dataset_dir = DATASET_ROOT / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)

    notes = _query_notes(db_path, args.keyword, args.limit)

    (dataset_dir / "xhs_notes.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_csv(dataset_dir / "xhs_notes.csv", notes)
    (dataset_dir / "summary.md").write_text(
        _build_summary(notes, args.keyword, dataset_id),
        encoding="utf-8",
    )
    (dataset_dir / "manifest.json").write_text(
        json.dumps(
            {
                "dataset_id": dataset_id,
                "source": "legacy-media-crawler-pro",
                "platform": "xhs",
                "db_path": db_path_input,
                "keyword": args.keyword,
                "limit": args.limit,
                "imported_count": len(notes),
                "imported_at": datetime.now().isoformat(timespec="seconds"),
                "files": {
                    "summary": "summary.md",
                    "json": "xhs_notes.json",
                    "csv": "xhs_notes.csv",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(dataset_dir)


if __name__ == "__main__":
    main()
