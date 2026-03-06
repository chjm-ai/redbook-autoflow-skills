#!/usr/bin/env python3
"""Import cdp_publish search-feeds output into shared xhs data-sources."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path


AUTO_FLOW_ROOT = Path(__file__).resolve().parent.parent
DATASET_ROOT = AUTO_FLOW_ROOT / "data-sources" / "xhs"
MARKER = "SEARCH_FEEDS_RESULT:"


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "all"


def _build_dataset_id(keyword: str, explicit_dataset_id: str | None) -> str:
    if explicit_dataset_id:
        return explicit_dataset_id.strip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"xhs_{_slugify(keyword)}_{timestamp}"


def _extract_payload(raw_text: str) -> dict:
    marker_index = raw_text.find(MARKER)
    if marker_index == -1:
        raise ValueError("SEARCH_FEEDS_RESULT marker not found")
    json_text = raw_text[marker_index + len(MARKER):].strip()
    return json.loads(json_text)


def _to_note(feed: dict) -> dict | None:
    if feed.get("modelType") != "note":
        return None
    note_card = feed.get("noteCard") or {}
    interact = note_card.get("interactInfo") or {}
    user = note_card.get("user") or {}
    cover = note_card.get("cover") or {}
    image_list = note_card.get("imageList") or []
    feed_id = feed.get("id", "")
    title = (note_card.get("displayTitle") or "").strip()
    if not title:
        title = f"无标题笔记 {str(feed_id)[:8]}"
    return {
        "id": feed_id,
        "note_id": feed_id,
        "title": title,
        "desc": title,
        "nickname": user.get("nickname") or user.get("nickName") or "",
        "liked_count": interact.get("likedCount", "0"),
        "collected_count": interact.get("collectedCount", "0"),
        "comment_count": interact.get("commentCount", "0"),
        "share_count": interact.get("sharedCount", "0"),
        "note_url": f"https://www.xiaohongshu.com/explore/{feed_id}?xsec_token={feed.get('xsecToken', '')}&xsec_source=pc_search",
        "source_keyword": "",
        "tag_list": "",
        "image_list": json.dumps(image_list, ensure_ascii=False),
        "time": note_card.get("cornerTagInfo", [{}])[0].get("text", ""),
        "cover_url": cover.get("urlDefault", ""),
        "xsec_token": feed.get("xsecToken", ""),
    }


def _build_summary(notes: list[dict], keyword: str, dataset_id: str) -> str:
    total = len(notes)
    lines = [
        "# 数据摘要",
        "",
        f"- 数据集: {dataset_id}",
        f"- 查询关键词: {keyword}",
        f"- 笔记总数: {total}",
        "",
        "## 热门样本",
        "",
    ]
    for idx, note in enumerate(notes[:10], start=1):
        lines.extend(
            [
                f"{idx}. {note['title']}",
                f"   - 作者: {note['nickname']}",
                f"   - 点赞/收藏/评论/分享: {note['liked_count']}/{note['collected_count']}/{note['comment_count']}/{note['share_count']}",
                f"   - 发布时间: {note['time']}",
                f"   - 链接: {note['note_url']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Writer 使用建议",
            "",
            "- 优先提炼高互动标题里的钩子表达，如‘一行配置’、‘绕过灰度入口’、‘正式确认发布’。",
            "- 结合高收藏内容，优先输出教程型、对比型、实测型文案。",
            "- 同一个数据集可支撑多个选题，每个选题再产出多个版本。",
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
        "cover_url",
        "xsec_token",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for note in notes:
            writer.writerow({key: note.get(key, "") for key in fieldnames})


def main():
    parser = argparse.ArgumentParser(description="Import cdp_publish search-feeds output into xhs data-sources.")
    parser.add_argument("--raw-file", required=True, help="Raw stdout file produced by cdp_publish search-feeds")
    parser.add_argument("--dataset-id", default=None)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    raw_text = Path(args.raw_file).read_text(encoding="utf-8")
    payload = _extract_payload(raw_text)
    keyword = payload.get("keyword", "")
    dataset_id = _build_dataset_id(keyword, args.dataset_id)
    dataset_dir = DATASET_ROOT / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)

    notes = []
    for feed in payload.get("feeds", []):
        note = _to_note(feed)
        if note:
            note["source_keyword"] = keyword
            notes.append(note)
        if len(notes) >= args.limit:
            break

    (dataset_dir / "xhs_notes.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_csv(dataset_dir / "xhs_notes.csv", notes)
    (dataset_dir / "summary.md").write_text(
        _build_summary(notes, keyword, dataset_id),
        encoding="utf-8",
    )
    (dataset_dir / "manifest.json").write_text(
        json.dumps(
            {
                "dataset_id": dataset_id,
                "source": "redbook-operator-search-feeds",
                "platform": "xhs",
                "keyword": keyword,
                "limit": args.limit,
                "imported_count": len(notes),
                "imported_at": datetime.now().isoformat(timespec="seconds"),
                "raw_file": args.raw_file,
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
