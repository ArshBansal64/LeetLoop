#!/usr/bin/env python3
"""Helpers for checking and updating LeetLoop .env files."""

from __future__ import annotations

import os
import sys
from pathlib import Path


PLACEHOLDERS = {
    "OPENAI_API_KEY": "your_openai_api_key_here",
    "LEETCODE_SESSION": "your_leetcode_session_here",
    "LEETCODE_CSRFTOKEN": "your_leetcode_csrf_here",
}


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def needs_configuration(path: Path) -> bool:
    data = parse_env_file(path)
    return any(not data.get(key, "").strip() or data.get(key, "").strip() == placeholder for key, placeholder in PLACEHOLDERS.items())


def update_env_file(path: Path, replacements: dict[str, str]) -> None:
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = content.splitlines() if content else [
        "OPENAI_API_KEY=your_openai_api_key_here",
        "OPENAI_MODEL=gpt-5.4",
        "LEETCODE_SESSION=your_leetcode_session_here",
        "LEETCODE_CSRFTOKEN=your_leetcode_csrf_here",
    ]

    updated: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if "=" not in line or line.lstrip().startswith("#"):
            updated.append(line)
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in replacements:
            updated.append(f"{key}={replacements[key]}")
            seen.add(key)
        else:
            updated.append(f"{key}={value}")

    for key, value in replacements.items():
        if key not in seen:
            updated.append(f"{key}={value}")

    path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: env_file_utils.py <needs-config|update> <env_path>")
        return 2

    command = sys.argv[1]
    path = Path(sys.argv[2])

    if command == "needs-config":
        return 0 if needs_configuration(path) else 1

    if command == "update":
        replacements = {
            "OPENAI_API_KEY": os.environ.get("LEETLOOP_SETUP_OPENAI_API_KEY", "").strip(),
            "LEETCODE_SESSION": os.environ.get("LEETLOOP_SETUP_LEETCODE_SESSION", "").strip(),
            "LEETCODE_CSRFTOKEN": os.environ.get("LEETLOOP_SETUP_LEETCODE_CSRFTOKEN", "").strip(),
        }
        missing = [key for key, value in replacements.items() if not value]
        if missing:
            print(f"Missing replacement values for: {', '.join(missing)}")
            return 1
        update_env_file(path, replacements)
        return 0

    print(f"Unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
