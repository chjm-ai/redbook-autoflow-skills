#!/usr/bin/env python3
"""High-level entrypoint for daily ops planning."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from attach_ops_plan import attach_ops_plan
from build_daily_plan import build_daily_plan
from collect_account_snapshot import collect_account_snapshot
from collect_trends import collect_trends
from ops_common import SKILLS_ROOT


AUTO_FLOW_INIT_RUN = SKILLS_ROOT / "redbook-auto-flow" / "scripts" / "init_run.py"
AUTO_FLOW_MATERIALIZE_SEARCH = (
    SKILLS_ROOT / "redbook-auto-flow" / "scripts" / "materialize_ops_search_dataset.py"
)


def _init_run(selected_keyword: str, explicit_run_id: str | None) -> str:
    cmd = [
        sys.executable,
        str(AUTO_FLOW_INIT_RUN),
        "--topic",
        selected_keyword,
        "--source-type",
        "ops",
    ]
    if explicit_run_id:
        cmd.extend(["--run-id", explicit_run_id])
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return Path(result.stdout.strip()).name


def run_daily_ops(
    account: str,
    domain: str,
    plan_id: str | None = None,
    run_id: str | None = None,
    page_num: int = 1,
    page_size: int = 10,
    note_type: int = 0,
    trend_provider: str = "google-news-rss",
    trend_limit: int = 10,
    keyword_limit: int = 10,
    reuse_existing_tab: bool = False,
    raw_content_data_text: str | None = None,
    raw_trend_payload: dict | None = None,
    materialize_search_dataset: bool = False,
) -> dict:
    """Run the full daily ops planning workflow."""
    snapshot_result = collect_account_snapshot(
        account=account,
        domain=domain,
        page_num=page_num,
        page_size=page_size,
        note_type=note_type,
        plan_id=plan_id,
        raw_text=raw_content_data_text,
        reuse_existing_tab=reuse_existing_tab,
    )
    plan_id = snapshot_result["plan_id"]

    collect_trends(
        account=account,
        domain=domain,
        provider_name=trend_provider,
        limit=trend_limit,
        plan_id=plan_id,
        raw_payload=raw_trend_payload,
    )
    plan_result = build_daily_plan(
        account=account,
        domain=domain,
        plan_id=plan_id,
        keyword_limit=keyword_limit,
    )
    resolved_run_id = _init_run(
        selected_keyword=plan_result["selected_keyword"],
        explicit_run_id=run_id,
    )
    ops_ref = attach_ops_plan(run_id=resolved_run_id, plan_id=plan_id)

    dataset_result = None
    if materialize_search_dataset:
        cmd = [
            sys.executable,
            str(AUTO_FLOW_MATERIALIZE_SEARCH),
            "--run-id",
            resolved_run_id,
        ]
        if account:
            cmd.extend(["--account", account])
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        dataset_result = json.loads(result.stdout.strip())

    return {
        "plan_id": plan_id,
        "run_id": resolved_run_id,
        "selected_keyword": ops_ref["selected_keyword"],
        "ops_ref": ops_ref,
        "dataset_result": dataset_result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the daily ops planning workflow.")
    parser.add_argument("--account", required=True, help="Target account name")
    parser.add_argument("--domain", required=True, help="Vertical domain label, e.g. AI 工具")
    parser.add_argument("--plan-id", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--page-num", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--note-type", type=int, default=0)
    parser.add_argument("--trend-provider", default="google-news-rss")
    parser.add_argument("--trend-limit", type=int, default=10)
    parser.add_argument("--keyword-limit", type=int, default=10)
    parser.add_argument("--reuse-existing-tab", action="store_true")
    parser.add_argument("--raw-content-data-file", default=None)
    parser.add_argument("--raw-trends-file", default=None)
    parser.add_argument("--materialize-search-dataset", action="store_true")
    args = parser.parse_args()

    raw_content_data_text = None
    if args.raw_content_data_file:
        raw_content_data_text = Path(args.raw_content_data_file).read_text(encoding="utf-8")

    raw_trend_payload = None
    if args.raw_trends_file:
        raw_trend_payload = json.loads(Path(args.raw_trends_file).read_text(encoding="utf-8"))

    result = run_daily_ops(
        account=args.account,
        domain=args.domain,
        plan_id=args.plan_id,
        run_id=args.run_id,
        page_num=args.page_num,
        page_size=args.page_size,
        note_type=args.note_type,
        trend_provider=args.trend_provider,
        trend_limit=args.trend_limit,
        keyword_limit=args.keyword_limit,
        reuse_existing_tab=args.reuse_existing_tab,
        raw_content_data_text=raw_content_data_text,
        raw_trend_payload=raw_trend_payload,
        materialize_search_dataset=args.materialize_search_dataset,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
