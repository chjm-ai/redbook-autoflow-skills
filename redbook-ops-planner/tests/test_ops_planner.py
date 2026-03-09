#!/usr/bin/env python3
"""Tests for the redbook-ops-planner workflow."""

from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_ROOT.parent / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from attach_ops_plan import attach_ops_plan  # noqa: E402
from build_daily_plan import build_daily_plan, generate_daily_keywords  # noqa: E402
from ops_common import (  # noqa: E402
    OPS_DATASET_ROOT,
    WORKSPACE_ROOT,
    dedupe_and_sort_trends,
    normalize_content_snapshot,
    write_json,
)


class OpsPlannerTests(unittest.TestCase):
    """End-to-end tests for ops planning helpers."""

    maxDiff = None

    def tearDown(self) -> None:
        for path in [
            OPS_DATASET_ROOT / "ops_testaccount_ai-tools_20260309",
            WORKSPACE_ROOT / "ops_test_run",
        ]:
            shutil.rmtree(path, ignore_errors=True)

    def test_normalize_content_snapshot(self) -> None:
        payload = {
            "request_url": "https://example.com/content-data",
            "requested_page_num": 1,
            "requested_page_size": 10,
            "requested_type": 0,
            "resolved_page_num": 1,
            "resolved_page_size": 10,
            "resolved_type": 0,
            "total": 2,
            "count_returned": 2,
            "rows": [
                {
                    "标题": "AI 工具实测：3 个搜索玩法",
                    "发布时间": "2026-03-08 10:00",
                    "曝光": "1200",
                    "观看": "560",
                    "封面点击率": "12.5%",
                    "点赞": "88",
                    "评论": "13",
                    "收藏": "42",
                    "涨粉": "9",
                    "分享": "7",
                    "人均观看时长": "36s",
                    "弹幕": "-",
                    "_id": "note_1",
                },
                {
                    "标题": "AI 工具清单：效率翻倍",
                    "发布时间": "2026-03-07 10:00",
                    "曝光": "500",
                    "观看": "200",
                    "封面点击率": "9%",
                    "点赞": "30",
                    "评论": "5",
                    "收藏": "20",
                    "涨粉": "3",
                    "分享": "2",
                    "人均观看时长": "20s",
                    "弹幕": "-",
                    "_id": "note_2",
                },
            ],
        }

        snapshot = normalize_content_snapshot(
            payload=payload,
            account="testaccount",
            domain="AI Tools",
            plan_id="ops_testaccount_ai-tools_20260309",
            collected_at="2026-03-09T09:00:00",
        )

        self.assertEqual(snapshot["account"], "testaccount")
        self.assertEqual(snapshot["rows"][0]["note_id"], "note_1")
        self.assertGreater(snapshot["rows"][0]["planning_score"], snapshot["rows"][1]["planning_score"])
        self.assertEqual(snapshot["top_patterns"][0]["pattern"], "实测")

    def test_dedupe_and_sort_trends(self) -> None:
        trends = [
            {
                "trend_id": "trend_01",
                "title": "AI 搜索更新",
                "summary": "A",
                "source_url": "https://example.com/a",
                "published_at": "2026-03-08T10:00:00+08:00",
                "source_name": "Example",
            },
            {
                "trend_id": "trend_02",
                "title": "AI 搜索更新",
                "summary": "B",
                "source_url": "https://example.com/a",
                "published_at": "2026-03-09T10:00:00+08:00",
                "source_name": "Example",
            },
            {
                "trend_id": "trend_03",
                "title": "大模型 Agent 发布",
                "summary": "C",
                "source_url": "https://example.com/b",
                "published_at": "2026-03-09T09:00:00+08:00",
                "source_name": "Example",
            },
        ]

        ranked = dedupe_and_sort_trends(trends)
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0]["trend_id"], "trend_02")

    def test_build_and_attach_daily_plan(self) -> None:
        plan_dir = OPS_DATASET_ROOT / "ops_testaccount_ai-tools_20260309"
        run_dir = WORKSPACE_ROOT / "ops_test_run"
        (run_dir / "inputs").mkdir(parents=True, exist_ok=True)
        write_json(
            run_dir / "metadata.json",
            {
                "run_id": "ops_test_run",
                "created_at": "2026-03-09T09:00:00",
                "source_type": "ops",
                "topic": "AI Tools",
                "status": "initialized",
                "dataset_id": None,
                "ops_plan_id": None,
                "selected_keyword": None,
                "account": None,
                "selected_candidate_ids": [],
            },
        )
        write_json(
            plan_dir / "account_snapshot.json",
            {
                "plan_id": "ops_testaccount_ai-tools_20260309",
                "account": "testaccount",
                "domain": "AI Tools",
                "collected_at": "2026-03-09T09:00:00",
                "top_patterns": [{"pattern": "教程", "score": 99, "examples": ["AI 教程"]}],
                "rows": [
                    {
                        "note_id": "n1",
                        "title": "AI 教程：搜索实战",
                        "planning_score": 123,
                    }
                ],
            },
        )
        write_json(
            plan_dir / "trend_briefs.json",
            {
                "plan_id": "ops_testaccount_ai-tools_20260309",
                "account": "testaccount",
                "domain": "AI Tools",
                "provider": "fixture",
                "count": 2,
                "trends": [
                    {
                        "trend_id": "trend_01",
                        "title": "OpenAI 发布 AI 搜索功能",
                        "summary": "搜索与 agent 协同增强",
                        "source_url": "https://example.com/a",
                        "published_at": "2026-03-09T08:00:00+08:00",
                        "source_name": "Example",
                    },
                    {
                        "trend_id": "trend_02",
                        "title": "Agent 工作流工具更新",
                        "summary": "自动化工具继续升温",
                        "source_url": "https://example.com/b",
                        "published_at": "2026-03-09T07:00:00+08:00",
                        "source_name": "Example",
                    },
                ],
            },
        )

        result = build_daily_plan(
            account="testaccount",
            domain="AI Tools",
            plan_id="ops_testaccount_ai-tools_20260309",
            keyword_limit=6,
        )
        self.assertTrue((plan_dir / "daily_keywords.json").exists())
        self.assertTrue(result["selected_keyword"])

        ops_ref = attach_ops_plan(
            run_id="ops_test_run",
            plan_id="ops_testaccount_ai-tools_20260309",
        )
        self.assertEqual(ops_ref["plan_id"], "ops_testaccount_ai-tools_20260309")
        self.assertTrue((run_dir / "inputs" / "ops_ref.json").exists())

    def test_generate_daily_keywords_contains_related_trends(self) -> None:
        payload = generate_daily_keywords(
            snapshot={
                "domain": "AI Tools",
                "top_patterns": [{"pattern": "教程", "score": 10, "examples": []}],
            },
            trend_payload={
                "trends": [
                    {
                        "trend_id": "trend_01",
                        "title": "AI 搜索 Agent 新功能",
                        "summary": "开发者正在关注 AI 搜索",
                    }
                ]
            },
            keyword_limit=5,
        )
        self.assertTrue(payload["keywords"])
        self.assertEqual(payload["keywords"][0]["related_trend_ids"], ["trend_01"])
        self.assertLessEqual(len(payload["selected_keyword"]), len("AI Tools agent"))
        self.assertNotIn("98.9", payload["selected_keyword"])
        self.assertEqual(payload["selected_keyword"].lower(), "ai tools agent")


if __name__ == "__main__":
    unittest.main()
