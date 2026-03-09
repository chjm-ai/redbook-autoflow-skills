#!/usr/bin/env python3
"""Tests for materializing ops-selected keywords into search datasets."""

from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TEST_ROOT.parent / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from materialize_ops_search_dataset import WORKSPACE_ROOT, materialize_ops_search_dataset  # noqa: E402


AUTO_FLOW_ROOT = TEST_ROOT.parent
OPS_DATASET_ROOT = AUTO_FLOW_ROOT / "data-sources" / "ops"
XHS_DATASET_ROOT = AUTO_FLOW_ROOT / "data-sources" / "xhs"


class MaterializeOpsSearchDatasetTests(unittest.TestCase):
    """Tests for the ops->search dataset bridge."""

    def tearDown(self) -> None:
        for path in [
            WORKSPACE_ROOT / "ops_search_test_run",
            OPS_DATASET_ROOT / "ops_testaccount_ai-tools_20260309",
            XHS_DATASET_ROOT / "xhs_ai_tools_agent_20260309",
        ]:
            shutil.rmtree(path, ignore_errors=True)

    def test_materialize_from_raw_search_file(self) -> None:
        run_dir = WORKSPACE_ROOT / "ops_search_test_run"
        (run_dir / "inputs").mkdir(parents=True, exist_ok=True)
        (run_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "run_id": "ops_search_test_run",
                    "created_at": "2026-03-09T09:00:00",
                    "source_type": "ops",
                    "topic": "AI Tools",
                    "status": "initialized",
                    "dataset_id": None,
                    "ops_plan_id": "ops_testaccount_ai-tools_20260309",
                    "selected_keyword": "AI Tools agent",
                    "account": "testaccount",
                    "selected_candidate_ids": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (run_dir / "inputs" / "ops_ref.json").write_text(
            json.dumps(
                {
                    "plan_id": "ops_testaccount_ai-tools_20260309",
                    "account": "testaccount",
                    "domain": "AI Tools",
                    "planned_at": "2026-03-09T09:00:00",
                    "selected_keyword": "AI Tools agent",
                    "paths": {},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        raw_search_text = """SEARCH_FEEDS_RESULT:
{
  "keyword": "AI Tools agent",
  "recommended_keywords": ["AI agent"],
  "feeds": [
    {
      "id": "feed_1",
      "modelType": "note",
      "xsecToken": "token_1",
      "noteCard": {
        "displayTitle": "AI agent 搜索实测",
        "interactInfo": {
          "likedCount": "100",
          "collectedCount": "50",
          "commentCount": "10",
          "sharedCount": "5"
        },
        "user": {
          "nickname": "作者A"
        },
        "cover": {
          "urlDefault": "https://example.com/cover.jpg"
        },
        "imageList": [],
        "cornerTagInfo": [
          {
            "text": "昨天"
          }
        ]
      }
    }
  ]
}
"""

        result = materialize_ops_search_dataset(
            run_id="ops_search_test_run",
            dataset_id="xhs_ai_tools_agent_20260309",
            raw_search_text=raw_search_text,
            limit=5,
        )
        self.assertEqual(result["dataset_id"], "xhs_ai_tools_agent_20260309")
        self.assertTrue((run_dir / "inputs" / "data_ref.json").exists())
        self.assertTrue((XHS_DATASET_ROOT / "xhs_ai_tools_agent_20260309" / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
