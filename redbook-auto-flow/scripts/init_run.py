#!/usr/bin/env python3
"""Create a redbook-auto-flow workspace for a single run."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


AUTO_FLOW_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = AUTO_FLOW_ROOT / "workspace"


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-")


def build_run_id(topic: str | None, explicit_run_id: str | None) -> str:
    if explicit_run_id:
        return explicit_run_id.strip()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slugify(topic or "")
    return f"{timestamp}_{slug}" if slug else timestamp


def main():
    parser = argparse.ArgumentParser(
        description="Create a redbook-auto-flow workspace directory."
    )
    parser.add_argument("--run-id", default=None, help="Explicit run_id to create")
    parser.add_argument("--topic", default="", help="Topic used to derive the run_id slug")
    parser.add_argument(
        "--source-type",
        default="direct",
        choices=["crawler", "notes", "search", "direct", "ops"],
        help="Initial source type recorded in metadata.json",
    )
    args = parser.parse_args()

    run_id = build_run_id(args.topic, args.run_id)
    run_dir = WORKSPACE_ROOT / run_id

    for relative in [
        "inputs",
        "topics",
        "candidates",
        "logs",
    ]:
        (run_dir / relative).mkdir(parents=True, exist_ok=True)

    metadata = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_type": args.source_type,
        "topic": args.topic,
        "status": "initialized",
        "dataset_id": None,
        "ops_plan_id": None,
        "selected_keyword": None,
        "account": None,
        "selected_candidate_ids": [],
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(run_dir)


if __name__ == "__main__":
    main()
