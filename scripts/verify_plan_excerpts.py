#!/usr/bin/env python3
"""Verify that marked task excerpts occur literally in their source plan."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


START = "<!-- PLAN_EXCERPT_START -->"
END = "<!-- PLAN_EXCERPT_END -->"
PLAN_LINK = re.compile(r"^Plan(?:o)?:\s*\[[^]]+\]\(([^)]+)\)\s*$", re.MULTILINE)
FENCED = re.compile(r"^(`{3,})text\r?\n(.*?)\r?\n\1\s*$", re.DOTALL)


def task_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(path for path in target.rglob("*.md") if path.name.lower() != "index.md")


def source_plan(task: Path, content: str, override: Path | None) -> Path:
    if override is not None:
        return override.resolve()
    match = PLAN_LINK.search(content)
    if not match:
        raise ValueError("missing 'Plan:' or 'Plano:' Markdown link")
    linked = match.group(1).split("#", 1)[0]
    return (task.parent / linked).resolve()


def excerpts(content: str) -> list[str]:
    blocks: list[str] = []
    cursor = 0
    while True:
        start = content.find(START, cursor)
        if start < 0:
            break
        end = content.find(END, start + len(START))
        if end < 0:
            raise ValueError("excerpt start has no matching end marker")
        wrapped = content[start + len(START):end].strip("\r\n")
        match = FENCED.fullmatch(wrapped)
        if not match:
            raise ValueError("excerpt must be wrapped in a matching text code fence")
        blocks.append(match.group(2).replace("\r\n", "\n"))
        cursor = end + len(END)
    if not blocks:
        raise ValueError("no marked plan excerpts found")
    return blocks


def verify(task: Path, override: Path | None) -> list[str]:
    content = task.read_text(encoding="utf-8")
    plan = source_plan(task, content, override)
    if not plan.is_file():
        raise ValueError(f"source plan does not exist: {plan}")
    plan_content = plan.read_text(encoding="utf-8").replace("\r\n", "\n")
    failures = []
    for number, excerpt in enumerate(excerpts(content), start=1):
        if excerpt not in plan_content:
            preview = excerpt.splitlines()[0] if excerpt else "<empty>"
            failures.append(f"excerpt {number} not found literally: {preview}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Task Markdown file or directory")
    parser.add_argument("--plan", type=Path, help="Override source plan for every task")
    args = parser.parse_args()

    files = task_files(args.target)
    if not files:
        print(f"ERROR: no task Markdown files found under {args.target}", file=sys.stderr)
        return 2

    failed = False
    for task in files:
        try:
            failures = verify(task, args.plan)
        except (OSError, UnicodeError, ValueError) as error:
            failures = [str(error)]
        if failures:
            failed = True
            print(f"FAIL {task}")
            for failure in failures:
                print(f"  - {failure}")
        else:
            print(f"OK   {task}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

