#!/usr/bin/env python3
"""Materialize the selected ops keyword into the existing XHS search dataset flow."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


AUTO_FLOW_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = AUTO_FLOW_ROOT / "workspace"
SKILLS_ROOT = AUTO_FLOW_ROOT.parent
OPERATOR_SCRIPT = SKILLS_ROOT / "redbook-operator" / "scripts" / "cdp_publish.py"
IMPORT_SCRIPT = AUTO_FLOW_ROOT / "scripts" / "import_xhs_search_payload.py"
ATTACH_SCRIPT = AUTO_FLOW_ROOT / "scripts" / "attach_dataset.py"


def materialize_ops_search_dataset(
    run_id: str,
    account: str | None = None,
    dataset_id: str | None = None,
    limit: int = 20,
    raw_search_text: str | None = None,
    reuse_existing_tab: bool = False,
) -> dict:
    """Turn the selected ops keyword into a shared search dataset and attach it."""
    run_dir = WORKSPACE_ROOT / run_id
    ops_ref_path = run_dir / "inputs" / "ops_ref.json"
    if not ops_ref_path.exists():
        raise SystemExit(f"ops_ref not found: {ops_ref_path}")

    ops_ref = json.loads(ops_ref_path.read_text(encoding="utf-8"))
    selected_keyword = ops_ref.get("selected_keyword", "").strip()
    if not selected_keyword:
        raise SystemExit(f"selected_keyword missing in {ops_ref_path}")

    if raw_search_text is None:
        cmd = [sys.executable, str(OPERATOR_SCRIPT)]
        resolved_account = account or ops_ref.get("account")
        if resolved_account:
            cmd.extend(["--account", resolved_account])
        if reuse_existing_tab:
            cmd.append("--reuse-existing-tab")
        cmd.extend(["search-feeds", "--keyword", selected_keyword])
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        raw_search_text = result.stdout

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix="_search.txt", delete=False) as handle:
        handle.write(raw_search_text)
        raw_file_path = Path(handle.name)

    import_cmd = [
        sys.executable,
        str(IMPORT_SCRIPT),
        "--raw-file",
        str(raw_file_path),
        "--limit",
        str(limit),
    ]
    if dataset_id:
        import_cmd.extend(["--dataset-id", dataset_id])
    import_result = subprocess.run(import_cmd, capture_output=True, text=True, check=True)
    dataset_dir = Path(import_result.stdout.strip())

    attach_cmd = [
        sys.executable,
        str(ATTACH_SCRIPT),
        "--run-id",
        run_id,
        "--dataset-id",
        dataset_dir.name,
    ]
    subprocess.run(attach_cmd, capture_output=True, text=True, check=True)

    try:
        raw_file_path.unlink(missing_ok=True)
    except OSError:
        pass

    return {
        "run_id": run_id,
        "dataset_id": dataset_dir.name,
        "dataset_dir": str(dataset_dir),
        "selected_keyword": selected_keyword,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize ops_ref selected_keyword into xhs data_ref.")
    parser.add_argument("--run-id", required=True, help="Existing run_id")
    parser.add_argument("--account", default=None, help="Optional account override for operator search")
    parser.add_argument("--dataset-id", default=None, help="Optional explicit dataset_id")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--raw-search-file", default=None, help="Optional raw stdout captured from search-feeds")
    parser.add_argument("--reuse-existing-tab", action="store_true")
    args = parser.parse_args()

    raw_search_text = None
    if args.raw_search_file:
        raw_search_text = Path(args.raw_search_file).read_text(encoding="utf-8")

    result = materialize_ops_search_dataset(
        run_id=args.run_id,
        account=args.account,
        dataset_id=args.dataset_id,
        limit=args.limit,
        raw_search_text=raw_search_text,
        reuse_existing_tab=args.reuse_existing_tab,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
