#!/usr/bin/env python3
"""Create a candidate workspace inside a run."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


AUTO_FLOW_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = AUTO_FLOW_ROOT / "workspace"


def main():
    parser = argparse.ArgumentParser(description="Create candidate directories for a run.")
    parser.add_argument("--run-id", required=True, help="Existing run_id")
    parser.add_argument("--candidate-id", required=True, help="Candidate id, e.g. topic_01")
    parser.add_argument("--topic-id", default="", help="Optional topic id reference")
    parser.add_argument("--title", default="", help="Optional candidate title")
    args = parser.parse_args()

    candidate_dir = WORKSPACE_ROOT / args.run_id / "candidates" / args.candidate_id
    for relative in ["drafts", "assets", "publish", "logs"]:
        (candidate_dir / relative).mkdir(parents=True, exist_ok=True)

    metadata = {
        "run_id": args.run_id,
        "candidate_id": args.candidate_id,
        "topic_id": args.topic_id,
        "title": args.title,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "initialized",
    }
    (candidate_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(candidate_dir)


if __name__ == "__main__":
    main()
