#!/usr/bin/env python3
"""Attach a shared dataset to a specific run."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


AUTO_FLOW_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = AUTO_FLOW_ROOT / "workspace"
DATASET_ROOT = AUTO_FLOW_ROOT / "data-sources" / "xhs"


def main():
    parser = argparse.ArgumentParser(description="Attach a dataset to a run.")
    parser.add_argument("--run-id", required=True, help="Existing run_id")
    parser.add_argument("--dataset-id", required=True, help="Existing dataset_id under data-sources/xhs")
    args = parser.parse_args()

    run_dir = WORKSPACE_ROOT / args.run_id
    dataset_dir = DATASET_ROOT / args.dataset_id
    if not run_dir.exists():
        raise SystemExit(f"run not found: {run_dir}")
    if not dataset_dir.exists():
        raise SystemExit(f"dataset not found: {dataset_dir}")

    manifest_path = dataset_dir / "manifest.json"
    source = "shared-dataset"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source = manifest.get("source") or source

    data_ref = {
        "dataset_id": args.dataset_id,
        "source": source,
        "attached_at": datetime.now().isoformat(timespec="seconds"),
        "paths": {
            "dataset_dir": f"data-sources/xhs/{args.dataset_id}",
            "summary": f"data-sources/xhs/{args.dataset_id}/summary.md",
            "json": f"data-sources/xhs/{args.dataset_id}/xhs_notes.json",
            "csv": f"data-sources/xhs/{args.dataset_id}/xhs_notes.csv",
            "manifest": f"data-sources/xhs/{args.dataset_id}/manifest.json",
        },
    }
    (run_dir / "inputs").mkdir(parents=True, exist_ok=True)
    (run_dir / "inputs" / "data_ref.json").write_text(
        json.dumps(data_ref, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    metadata_path = run_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["dataset_id"] = args.dataset_id
    metadata["updated_at"] = datetime.now().isoformat(timespec="seconds")
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(run_dir / "inputs" / "data_ref.json")


if __name__ == "__main__":
    main()
