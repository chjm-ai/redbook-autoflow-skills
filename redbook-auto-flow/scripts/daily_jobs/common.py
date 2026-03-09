#!/usr/bin/env python3
"""Common utilities for daily job scheduling.

This module provides shared functionality for all daily job steps including:
- Path resolution and workspace management
- State file I/O with atomic writes
- Context management for run_context.json
- Logging utilities
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Path constants
SCRIPT_DIR = Path(__file__).resolve().parent
DAILY_JOBS_DIR = SCRIPT_DIR
AUTO_FLOW_ROOT = SCRIPT_DIR.parent.parent
WORKSPACE_ROOT = AUTO_FLOW_ROOT / "workspace"
DAILY_JOBS_WORKSPACE = WORKSPACE_ROOT / "daily-jobs"
SKILLS_ROOT = AUTO_FLOW_ROOT.parent

# Other skill paths
OPS_PLANNER_DIR = SKILLS_ROOT / "redbook-ops-planner"
OPERATOR_DIR = SKILLS_ROOT / "redbook-operator"
WRITER_DIR = SKILLS_ROOT / "redbook-writer"
ILLUSTRATOR_DIR = SKILLS_ROOT / "redbook-illustrator"

# Fixed safe keyword pool for first version
SAFE_KEYWORD_POOL = [
    "AI 工具 教程",
    "AI 工作流",
    "AI 自动化",
    "OpenClaw 教程",
    "OpenClaw skill",
    "Claude Code 工作流",
    "AI agent 教程",
    "AI 提效工具",
]

# Status constants
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"


def get_today_str() -> str:
    """Return today's date as YYYYMMDD string."""
    return datetime.now().strftime("%Y%m%d")


def get_daily_job_dir(date_str: str | None = None) -> Path:
    """Get the daily job directory for a specific date.
    
    Args:
        date_str: Date in YYYYMMDD format. Defaults to today.
    
    Returns:
        Path to the daily job directory.
    """
    if date_str is None:
        date_str = get_today_str()
    return DAILY_JOBS_WORKSPACE / date_str


def ensure_daily_job_dir(date_str: str | None = None) -> Path:
    """Ensure the daily job directory exists, create if not.
    
    Args:
        date_str: Date in YYYYMMDD format. Defaults to today.
    
    Returns:
        Path to the daily job directory.
    """
    job_dir = get_daily_job_dir(date_str)
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "logs").mkdir(parents=True, exist_ok=True)
    return job_dir


def write_json_atomic(path: Path, data: Any) -> None:
    """Write JSON file atomically (write to temp then rename).
    
    Args:
        path: Target file path.
        data: Data to serialize as JSON.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    temp_path.rename(path)


def read_json(path: Path, default: Any | None = None) -> Any:
    """Read JSON file, return default if not exists.
    
    Args:
        path: File path to read.
        default: Default value if file doesn't exist.
    
    Returns:
        Parsed JSON data or default.
    """
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def init_run_context(
    date_str: str,
    account: str,
    domain: str,
    force_reset: bool = False,
) -> dict[str, Any]:
    """Initialize or load run_context.json for a date.
    
    Args:
        date_str: Date in YYYYMMDD format.
        account: Account name.
        domain: Domain/category.
        force_reset: If True, reset existing context.
    
    Returns:
        The run context dict.
    """
    job_dir = ensure_daily_job_dir(date_str)
    context_path = job_dir / "run_context.json"
    
    if not force_reset and context_path.exists():
        return read_json(context_path)
    
    context = {
        "date": date_str,
        "account": account,
        "domain": domain,
        "run_id": None,
        "plan_id": None,
        "dataset_id": None,
        "selected_keyword": None,
        "selected_candidate_id": None,
        "status": STATUS_PENDING,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    write_json_atomic(context_path, context)
    return context


def update_run_context(date_str: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Update run_context.json with new values.
    
    Args:
        date_str: Date in YYYYMMDD format.
        updates: Dict of fields to update.
    
    Returns:
        Updated context dict.
    """
    job_dir = get_daily_job_dir(date_str)
    context_path = job_dir / "run_context.json"
    context = read_json(context_path, {})
    context.update(updates)
    context["updated_at"] = datetime.now().isoformat(timespec="seconds")
    write_json_atomic(context_path, context)
    return context


def get_run_context(date_str: str) -> dict[str, Any] | None:
    """Get run_context.json for a date.
    
    Args:
        date_str: Date in YYYYMMDD format.
    
    Returns:
        Context dict or None if not exists.
    """
    job_dir = get_daily_job_dir(date_str)
    context_path = job_dir / "run_context.json"
    return read_json(context_path, None)


def write_step_status(
    date_str: str,
    step: str,
    status: str,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    error: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> dict[str, Any]:
    """Write step status file.
    
    Args:
        date_str: Date in YYYYMMDD format.
        step: Step name (e.g., "step_a_ops").
        status: Step status.
        inputs: Input parameters.
        outputs: Output results.
        error: Error message if failed.
        started_at: Start timestamp.
        finished_at: Finish timestamp.
    
    Returns:
        The step status dict.
    """
    job_dir = ensure_daily_job_dir(date_str)
    step_path = job_dir / f"{step}.json"
    
    step_data = read_json(step_path, {})
    step_data["step"] = step
    step_data["status"] = status
    
    if started_at:
        step_data["started_at"] = started_at
    if finished_at:
        step_data["finished_at"] = finished_at
    if inputs is not None:
        step_data["inputs"] = inputs
    if outputs is not None:
        step_data["outputs"] = outputs
    if error is not None:
        step_data["error"] = error
    
    step_data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    write_json_atomic(step_path, step_data)
    return step_data


def get_step_status(date_str: str, step: str) -> dict[str, Any] | None:
    """Get step status for a date.
    
    Args:
        date_str: Date in YYYYMMDD format.
        step: Step name.
    
    Returns:
        Step status dict or None.
    """
    job_dir = get_daily_job_dir(date_str)
    step_path = job_dir / f"{step}.json"
    return read_json(step_path, None)


def check_prerequisite_step(date_str: str, prerequisite_step: str) -> dict[str, Any]:
    """Check if a prerequisite step is completed.
    
    Args:
        date_str: Date in YYYYMMDD format.
        prerequisite_step: Name of the prerequisite step.
    
    Returns:
        The step status dict if successful.
    
    Raises:
        SystemExit: If prerequisite not met.
    """
    step_status = get_step_status(date_str, prerequisite_step)
    if not step_status:
        print(f"Error: Prerequisite step '{prerequisite_step}' not found.", file=sys.stderr)
        sys.exit(1)
    if step_status.get("status") != STATUS_SUCCESS:
        print(
            f"Error: Prerequisite step '{prerequisite_step}' status is '{step_status.get('status')}'. "
            "Please run it first.",
            file=sys.stderr
        )
        sys.exit(1)
    return step_status


def select_keyword_from_pool(
    account_snapshot: dict[str, Any] | None = None,
    default_keyword: str = "AI 工作流",
) -> str:
    """Select a keyword from the safe pool based on account data.
    
    For the first version, this uses a simple selection strategy:
    - If account has high-performing "工作流" content, prefer "AI 工作流"
    - If account has high-performing "教程" content, prefer "AI 工具 教程"
    - Otherwise rotate through the pool based on day of week
    
    Args:
        account_snapshot: Optional account snapshot data.
        default_keyword: Fallback keyword.
    
    Returns:
        Selected keyword.
    """
    # Simple rotation based on day of week for first version
    day_of_week = datetime.now().weekday()
    
    # If we have account data, try to match patterns
    if account_snapshot:
        top_patterns = account_snapshot.get("top_patterns", [])
        pattern_names = [p.get("pattern", "") for p in top_patterns]
        
        if "教程" in pattern_names:
            return "AI 工具 教程"
        elif "工作流" in str(account_snapshot):
            return "AI 工作流"
    
    # Rotate through pool
    return SAFE_KEYWORD_POOL[day_of_week % len(SAFE_KEYWORD_POOL)]


def log_message(date_str: str, message: str, level: str = "INFO") -> None:
    """Log a message to the daily job log file and stdout.
    
    Args:
        date_str: Date in YYYYMMDD format.
        message: Log message.
        level: Log level.
    """
    timestamp = datetime.now().isoformat(timespec="seconds")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)
    
    job_dir = get_daily_job_dir(date_str)
    log_path = job_dir / "logs" / "daily_job.log"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def get_run_workspace_dir(run_id: str) -> Path:
    """Get the workspace directory for a specific run_id.
    
    Args:
        run_id: The run ID.
    
    Returns:
        Path to the run workspace.
    """
    return WORKSPACE_ROOT / run_id


def get_candidate_dir(run_id: str, candidate_id: str) -> Path:
    """Get the candidate directory for a specific candidate.
    
    Args:
        run_id: The run ID.
        candidate_id: The candidate ID.
    
    Returns:
        Path to the candidate directory.
    """
    return get_run_workspace_dir(run_id) / "candidates" / candidate_id


def find_candidates(run_id: str) -> list[str]:
    """Find all candidate IDs for a run.
    
    Args:
        run_id: The run ID.
    
    Returns:
        List of candidate IDs.
    """
    run_dir = get_run_workspace_dir(run_id)
    candidates_dir = run_dir / "candidates"
    if not candidates_dir.exists():
        return []
    return sorted([d.name for d in candidates_dir.iterdir() if d.is_dir()])


def select_best_candidate(run_id: str) -> tuple[str, dict[str, Any]] | None:
    """Automatically select the best candidate for publishing.
    
    Selection rules:
    1. Must have drafts/final.md
    2. Prioritize candidates with metadata score
    3. Otherwise select first valid candidate
    
    Args:
        run_id: The run ID.
    
    Returns:
        Tuple of (candidate_id, metadata) or None.
    """
    candidates = find_candidates(run_id)
    if not candidates:
        return None
    
    scored_candidates: list[tuple[str, dict[str, Any], float]] = []
    
    for candidate_id in candidates:
        candidate_dir = get_candidate_dir(run_id, candidate_id)
        final_md = candidate_dir / "drafts" / "final.md"
        metadata_path = candidate_dir / "metadata.json"
        
        # Must have final.md
        if not final_md.exists():
            continue
        
        metadata = read_json(metadata_path, {})
        score = metadata.get("score", 0) or 0
        scored_candidates.append((candidate_id, metadata, score))
    
    if not scored_candidates:
        return None
    
    # Sort by score descending
    scored_candidates.sort(key=lambda x: x[2], reverse=True)
    best = scored_candidates[0]
    return best[0], best[1]


class StepRunner:
    """Context manager for running a step with proper status tracking."""
    
    def __init__(
        self,
        date_str: str,
        step_name: str,
        inputs: dict[str, Any] | None = None,
    ):
        self.date_str = date_str
        self.step_name = step_name
        self.inputs = inputs or {}
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self.finished_at: str | None = None
        self.outputs: dict[str, Any] = {}
        self.error: str | None = None
    
    def __enter__(self) -> "StepRunner":
        """Mark step as running."""
        log_message(self.date_str, f"Starting {self.step_name}")
        write_step_status(
            self.date_str,
            self.step_name,
            STATUS_RUNNING,
            inputs=self.inputs,
            started_at=self.started_at,
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Mark step as success or failed."""
        self.finished_at = datetime.now().isoformat(timespec="seconds")
        
        if exc_val is not None:
            self.error = str(exc_val)
            write_step_status(
                self.date_str,
                self.step_name,
                STATUS_FAILED,
                inputs=self.inputs,
                outputs=self.outputs,
                error=self.error,
                started_at=self.started_at,
                finished_at=self.finished_at,
            )
            log_message(self.date_str, f"{self.step_name} failed: {self.error}", "ERROR")
            return False  # Re-raise exception
        
        write_step_status(
            self.date_str,
            self.step_name,
            STATUS_SUCCESS,
            inputs=self.inputs,
            outputs=self.outputs,
            started_at=self.started_at,
            finished_at=self.finished_at,
        )
        log_message(self.date_str, f"{self.step_name} completed successfully")
        return True
    
    def set_output(self, key: str, value: Any) -> None:
        """Set an output value."""
        self.outputs[key] = value


if __name__ == "__main__":
    # Simple test
    print("Common module loaded successfully")
    print(f"Daily jobs workspace: {DAILY_JOBS_WORKSPACE}")
    print(f"Safe keyword pool: {SAFE_KEYWORD_POOL}")
