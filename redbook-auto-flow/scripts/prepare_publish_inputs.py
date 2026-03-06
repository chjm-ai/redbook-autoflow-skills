#!/usr/bin/env python3
"""Extract title/content from a candidate final markdown into publish inputs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


AUTO_FLOW_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = AUTO_FLOW_ROOT / "workspace"


def _strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)


def _extract_title_and_body(markdown: str) -> tuple[str, str]:
    body = _strip_frontmatter(markdown).strip()
    lines = body.splitlines()
    title = ""
    remaining = []
    for idx, line in enumerate(lines):
        if line.strip().startswith("# "):
            title = line.strip()[2:].strip()
            remaining = lines[idx + 1 :]
            break
    if not title:
        for idx, line in enumerate(lines):
            if line.strip():
                title = line.strip()
                remaining = lines[idx + 1 :]
                break
    content = "\n".join(remaining).strip()
    return title, content


def main():
    parser = argparse.ArgumentParser(description="Prepare publish/title.txt and publish/content.txt from final.md.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--candidate-id", required=True)
    args = parser.parse_args()

    candidate_dir = WORKSPACE_ROOT / args.run_id / "candidates" / args.candidate_id
    final_path = candidate_dir / "drafts" / "final.md"
    if not final_path.exists():
        raise SystemExit(f"final markdown not found: {final_path}")

    title, content = _extract_title_and_body(final_path.read_text(encoding="utf-8"))
    publish_dir = candidate_dir / "publish"
    publish_dir.mkdir(parents=True, exist_ok=True)
    (publish_dir / "title.txt").write_text(title.strip() + "\n", encoding="utf-8")
    (publish_dir / "content.txt").write_text(content.strip() + "\n", encoding="utf-8")

    print(publish_dir)


if __name__ == "__main__":
    main()
