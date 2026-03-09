#!/usr/bin/env python3
"""Collect the latest account performance snapshot into an ops plan directory."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ops_common import (
    CONTENT_DATA_MARKER,
    SKILLS_ROOT,
    extract_json_after_marker,
    get_plan_dir,
    normalize_content_snapshot,
    write_json,
    write_snapshot_csv,
)


OPERATOR_SCRIPT = SKILLS_ROOT / "redbook-operator" / "scripts" / "cdp_publish.py"


def collect_account_snapshot(
    account: str,
    domain: str,
    page_num: int = 1,
    page_size: int = 10,
    note_type: int = 0,
    plan_id: str | None = None,
    raw_text: str | None = None,
    reuse_existing_tab: bool = False,
) -> dict:
    """Collect and persist a normalized content snapshot."""
    resolved_plan_id, plan_dir = get_plan_dir(account=account, domain=domain, explicit_plan_id=plan_id)
    plan_dir.mkdir(parents=True, exist_ok=True)

    if raw_text is None:
        cmd = [
            sys.executable,
            str(OPERATOR_SCRIPT),
            "--account",
            account,
        ]
        if reuse_existing_tab:
            cmd.append("--reuse-existing-tab")
        cmd.extend([
            "content-data",
            "--page-num",
            str(page_num),
            "--page-size",
            str(page_size),
            "--type",
            str(note_type),
        ])
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        raw_text = result.stdout

    payload = extract_json_after_marker(raw_text, CONTENT_DATA_MARKER)
    snapshot = normalize_content_snapshot(
        payload=payload,
        account=account,
        domain=domain,
        plan_id=resolved_plan_id,
    )
    write_json(plan_dir / "account_snapshot.json", snapshot)
    write_snapshot_csv(plan_dir / "account_snapshot.csv", snapshot["rows"])
    return {
        "plan_id": resolved_plan_id,
        "plan_dir": str(plan_dir),
        "snapshot": snapshot,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect account content-data into an ops plan directory.")
    parser.add_argument("--account", required=True, help="Target account name")
    parser.add_argument("--domain", required=True, help="Vertical domain label, e.g. AI 工具")
    parser.add_argument("--plan-id", default=None, help="Explicit ops plan id")
    parser.add_argument("--page-num", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--note-type", type=int, default=0)
    parser.add_argument("--raw-file", default=None, help="Optional raw stdout captured from cdp_publish content-data")
    parser.add_argument("--reuse-existing-tab", action="store_true")
    args = parser.parse_args()

    raw_text = None
    if args.raw_file:
        raw_text = Path(args.raw_file).read_text(encoding="utf-8")

    result = collect_account_snapshot(
        account=args.account,
        domain=args.domain,
        page_num=args.page_num,
        page_size=args.page_size,
        note_type=args.note_type,
        plan_id=args.plan_id,
        raw_text=raw_text,
        reuse_existing_tab=args.reuse_existing_tab,
    )
    print(result["plan_dir"])


if __name__ == "__main__":
    main()
