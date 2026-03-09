#!/usr/bin/env python3
"""Attach an ops plan to an existing redbook-auto-flow run."""

from __future__ import annotations

import argparse
from datetime import datetime

from ops_common import AUTO_FLOW_ROOT, WORKSPACE_ROOT, read_json, write_json


OPS_DATASET_ROOT = AUTO_FLOW_ROOT / "data-sources" / "ops"


def attach_ops_plan(run_id: str, plan_id: str) -> dict:
    """Write ops_ref.json and update run metadata."""
    run_dir = WORKSPACE_ROOT / run_id
    plan_dir = OPS_DATASET_ROOT / plan_id
    if not run_dir.exists():
        raise SystemExit(f"run not found: {run_dir}")
    if not plan_dir.exists():
        raise SystemExit(f"ops plan not found: {plan_dir}")

    manifest = read_json(plan_dir / "manifest.json")
    daily_keywords = read_json(plan_dir / "daily_keywords.json")

    ops_ref = {
        "plan_id": plan_id,
        "account": manifest.get("account", ""),
        "domain": manifest.get("domain", ""),
        "planned_at": manifest.get("planned_at", ""),
        "selected_keyword": daily_keywords.get("selected_keyword", ""),
        "paths": {
            "plan_dir": f"data-sources/ops/{plan_id}",
            "summary": f"data-sources/ops/{plan_id}/planning_summary.md",
            "keywords": f"data-sources/ops/{plan_id}/daily_keywords.json",
            "account_snapshot": f"data-sources/ops/{plan_id}/account_snapshot.json",
        },
    }
    write_json(run_dir / "inputs" / "ops_ref.json", ops_ref)

    metadata_path = run_dir / "metadata.json"
    metadata = read_json(metadata_path)
    metadata["ops_plan_id"] = plan_id
    metadata["selected_keyword"] = ops_ref["selected_keyword"]
    metadata["account"] = ops_ref["account"]
    metadata["updated_at"] = datetime.now().isoformat(timespec="seconds")
    write_json(metadata_path, metadata)

    return ops_ref


def main() -> None:
    parser = argparse.ArgumentParser(description="Attach an ops plan to a run.")
    parser.add_argument("--run-id", required=True, help="Existing run_id")
    parser.add_argument("--plan-id", required=True, help="Existing ops plan id under data-sources/ops")
    args = parser.parse_args()

    attach_ops_plan(run_id=args.run_id, plan_id=args.plan_id)
    print(WORKSPACE_ROOT / args.run_id / "inputs" / "ops_ref.json")


if __name__ == "__main__":
    main()
