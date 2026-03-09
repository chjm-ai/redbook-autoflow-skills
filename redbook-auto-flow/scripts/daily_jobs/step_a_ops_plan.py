#!/usr/bin/env python3
"""Step A: Generate daily ops plan.

This step:
1. Creates or reads the daily job directory
2. Calls redbook-ops-planner to collect account data (without external news)
3. Selects a safe keyword from the fixed pool based on account performance
4. Creates plan_id and run_id
5. Mounts ops_ref.json
6. Updates run_context.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (
    AUTO_FLOW_ROOT,
    DAILY_JOBS_ROOT,
    SKILLS_ROOT,
    ensure_daily_job_dir,
    get_daily_job_dir,
    get_run_context_path,
    load_run_context,
    log_error,
    log_info,
    log_success,
    save_run_context,
    save_step_status,
    select_keyword_from_pool,
    validate_selected_keyword,
    slugify,
)


# Script paths
OPS_PLANNER_ROOT = SKILLS_ROOT / "redbook-ops-planner"
COLLECT_SNAPSHOT_SCRIPT = OPS_PLANNER_ROOT / "scripts" / "collect_account_snapshot.py"
BUILD_DAILY_PLAN_SCRIPT = OPS_PLANNER_ROOT / "scripts" / "build_daily_plan.py"
ATTACH_OPS_PLAN_SCRIPT = OPS_PLANNER_ROOT / "scripts" / "attach_ops_plan.py"
INIT_RUN_SCRIPT = AUTO_FLOW_ROOT / "scripts" / "init_run.py"


def run_collect_account_snapshot(
    account: str,
    domain: str,
    date_str: str,
) -> dict[str, Any]:
    """Collect account content data snapshot."""
    log_info(f"Collecting account snapshot for {account}...")
    
    # First, collect raw content data
    cmd = [
        sys.executable,
        str(SKILLS_ROOT / "redbook-operator" / "scripts" / "cdp_publish.py"),
        "--account", account,
        "content-data",
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to collect content data: {result.stderr}")
    
    # Parse content data
    marker = "CONTENT_DATA_RESULT:"
    if marker in result.stdout:
        json_text = result.stdout[result.stdout.find(marker) + len(marker):].strip()
        content_data = json.loads(json_text)
    else:
        # Try to find JSON in output
        content_data = {"rows": []}
    
    # Normalize and analyze
    from ops_common import normalize_content_snapshot, compute_planning_score, parse_numeric
    
    snapshot = normalize_content_snapshot(
        payload={
            "rows": content_data.get("rows", []),
            "total": content_data.get("total", 0),
        },
        account=account,
        domain=domain,
        plan_id=f"ops_{slugify(account)}_{slugify(domain)}_{date_str}",
        collected_at=datetime.now().isoformat(timespec="seconds"),
    )
    
    return snapshot


def build_ops_plan(
    account: str,
    domain: str,
    date_str: str,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Build ops plan from account snapshot (without external trends)."""
    log_info("Building daily ops plan...")
    
    plan_id = f"ops_{slugify(account)}_{slugify(domain)}_{date_str}"
    plan_dir = AUTO_FLOW_ROOT / "data-sources" / "ops" / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    
    # Save snapshot
    snapshot_path = plan_dir / "account_snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    
    # Generate CSV
    from ops_common import write_snapshot_csv
    write_snapshot_csv(plan_dir / "account_snapshot.csv", snapshot.get("rows", []))
    
    # Select keyword from fixed pool based on account performance
    selected_keyword = select_keyword_from_pool(snapshot)
    selected_keyword = validate_selected_keyword(selected_keyword)
    
    log_info(f"Selected keyword: {selected_keyword}")
    
    # Get top patterns for summary
    top_patterns = snapshot.get("top_patterns", [])
    lead_pattern = top_patterns[0]["pattern"] if top_patterns else "教程"
    
    # Build planning summary
    summary_lines = [
        "# 每日运营规划",
        "",
        f"- 账号: {account}",
        f"- 垂类: {domain}",
        f"- 计划时间: {datetime.now().isoformat(timespec='seconds')}",
        f"- 今日主推关键词: {selected_keyword}",
        "",
        "## 账号侧观察",
        "",
    ]
    
    rows = snapshot.get("rows", [])
    if rows:
        top_row = rows[0]
        summary_lines.append(
            f"- 近期表现最好的笔记是《{top_row.get('title', '-')}》，规划分 {top_row.get('planning_score', 0)}。"
        )
    
    if top_patterns:
        patterns_text = "、".join(item["pattern"] for item in top_patterns[:3])
        summary_lines.append(f"- 账号近期更适合继续放大这几类表达：{patterns_text}。")
    
    summary_lines.extend([
        "",
        "## 执行建议",
        "",
        f"- 先用 `{selected_keyword}` 跑小红书站内搜索，再进入现有 writer / illustrator / publish 链路。",
        "- 发布动作默认保留人工确认，不直接自动点发布。",
    ])
    
    summary_md = "\n".join(summary_lines)
    
    # Build daily keywords
    daily_keywords = {
        "plan_id": plan_id,
        "account": account,
        "domain": domain,
        "planned_at": datetime.now().isoformat(timespec="seconds"),
        "lead_pattern": lead_pattern,
        "selected_keyword": selected_keyword,
        "keywords": [
            {
                "keyword": selected_keyword,
                "reason": f"基于账号表现，从固定安全词池中选择。",
                "related_trend_ids": [],
                "score": 80,
            }
        ],
    }
    
    # Save files
    (plan_dir / "daily_keywords.json").write_text(
        json.dumps(daily_keywords, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (plan_dir / "planning_summary.md").write_text(summary_md, encoding="utf-8")
    
    # Create manifest
    manifest = {
        "plan_id": plan_id,
        "account": account,
        "domain": domain,
        "planned_at": daily_keywords["planned_at"],
        "selected_keyword": selected_keyword,
        "files": {
            "account_snapshot": "account_snapshot.json",
            "account_snapshot_csv": "account_snapshot.csv",
            "daily_keywords": "daily_keywords.json",
            "planning_summary": "planning_summary.md",
        },
    }
    (plan_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    
    return {
        "plan_id": plan_id,
        "plan_dir": str(plan_dir),
        "selected_keyword": selected_keyword,
        "lead_pattern": lead_pattern,
    }


def create_run_and_attach_ops(
    plan_result: dict[str, Any],
    date_str: str,
) -> dict[str, Any]:
    """Create run and attach ops plan."""
    log_info("Creating run and attaching ops plan...")
    
    selected_keyword = plan_result["selected_keyword"]
    plan_id = plan_result["plan_id"]
    
    # Create run_id based on date and keyword
    run_id = f"{date_str}_{slugify(selected_keyword)}"
    
    # Initialize run
    cmd = [
        sys.executable,
        str(INIT_RUN_SCRIPT),
        "--run-id", run_id,
        "--topic", selected_keyword,
        "--source-type", "ops",
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to init run: {result.stderr}")
    
    run_dir = Path(result.stdout.strip())
    log_info(f"Created run: {run_id}")
    
    # Attach ops plan
    cmd = [
        sys.executable,
        str(ATTACH_OPS_PLAN_SCRIPT),
        "--run-id", run_id,
        "--plan-id", plan_id,
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to attach ops plan: {result.stderr}")
    
    ops_ref = json.loads(result.stdout.strip())
    log_info(f"Attached ops plan: {plan_id}")
    
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "plan_id": plan_id,
        "ops_ref": ops_ref,
    }


def main():
    parser = argparse.ArgumentParser(description="Step A: Generate daily ops plan.")
    parser.add_argument("--date", default=None, help="Date in YYYYMMDD format (default: today)")
    parser.add_argument("--account", required=True, help="Target account name")
    parser.add_argument("--domain", default="AI工具", help="Vertical domain label")
    parser.add_argument("--force", action="store_true", help="Force re-run even if already completed")
    args = parser.parse_args()
    
    date_str = args.date or datetime.now().strftime("%Y%m%d")
    
    # Check if already completed
    if not args.force:
        status = load_step_status("step_a_ops_plan", date_str)
        if status and status.get("status") == "success":
            log_info(f"Step A already completed for {date_str}")
            print(json.dumps(status.get("data", {}), ensure_ascii=False))
            return
    
    try:
        ensure_daily_job_dir(date_str)
        
        # Step A.1: Collect account snapshot
        snapshot = run_collect_account_snapshot(args.account, args.domain, date_str)
        
        # Step A.2: Build ops plan
        plan_result = build_ops_plan(args.account, args.domain, date_str, snapshot)
        
        # Step A.3: Create run and attach ops
        run_result = create_run_and_attach_ops(plan_result, date_str)
        
        # Save run context
        context = {
            "date": date_str,
            "account": args.account,
            "domain": args.domain,
            "plan_id": plan_result["plan_id"],
            "run_id": run_result["run_id"],
            "selected_keyword": plan_result["selected_keyword"],
            "lead_pattern": plan_result["lead_pattern"],
            "status": "ops_plan_completed",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        save_run_context(context, date_str)
        
        # Save step status
        result_data = {
            "plan_id": plan_result["plan_id"],
            "run_id": run_result["run_id"],
            "selected_keyword": plan_result["selected_keyword"],
            "run_dir": run_result["run_dir"],
        }
        save_step_status("step_a_ops_plan", "success", result_data, date_str)
        
        log_success(f"Step A completed: run_id={run_result['run_id']}, keyword={plan_result['selected_keyword']}")
        print(json.dumps(result_data, ensure_ascii=False))
        
    except Exception as e:
        log_error(f"Step A failed: {e}")
        save_step_status("step_a_ops_plan", "failed", {"error": str(e)}, date_str)
        sys.exit(1)


if __name__ == "__main__":
    # Add ops_common to path for imports
    sys.path.insert(0, str(OPS_PLANNER_ROOT / "scripts"))
    from ops_common import normalize_content_snapshot, compute_planning_score, parse_numeric, write_snapshot_csv
    
    main()
