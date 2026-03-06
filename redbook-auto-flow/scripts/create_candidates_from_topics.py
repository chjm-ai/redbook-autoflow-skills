#!/usr/bin/env python3
"""Create candidate directories from selected topic ids."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


AUTO_FLOW_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = AUTO_FLOW_ROOT / "workspace"


def main():
    parser = argparse.ArgumentParser(description="Create candidates from topics.json entries.")
    parser.add_argument("--run-id", required=True, help="Existing run_id")
    parser.add_argument("--topic-ids", nargs="+", required=True, help="Topic ids to materialize")
    parser.add_argument("--variants", type=int, default=1, help="Planned draft count per topic")
    args = parser.parse_args()

    run_dir = WORKSPACE_ROOT / args.run_id
    topics_path = run_dir / "topics" / "topics.json"
    if not topics_path.exists():
        raise SystemExit(f"topics not found: {topics_path}")

    topics_payload = json.loads(topics_path.read_text(encoding="utf-8"))
    topics = topics_payload.get("topics", topics_payload if isinstance(topics_payload, list) else [])
    by_id = {topic.get("topic_id"): topic for topic in topics if isinstance(topic, dict)}

    created = []
    for topic_id in args.topic_ids:
        topic = by_id.get(topic_id)
        if not topic:
            raise SystemExit(f"topic_id not found: {topic_id}")

        candidate_id = topic_id
        candidate_dir = run_dir / "candidates" / candidate_id
        for relative in ["drafts", "assets", "publish", "logs"]:
            (candidate_dir / relative).mkdir(parents=True, exist_ok=True)
        metadata = {
            "run_id": args.run_id,
            "candidate_id": candidate_id,
            "topic_id": topic_id,
            "title": topic.get("title", ""),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "initialized",
            "planned_variants": args.variants,
        }
        (candidate_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        created.append(candidate_id)

    print(json.dumps({"run_id": args.run_id, "created_candidate_ids": created}, ensure_ascii=False))


if __name__ == "__main__":
    main()
