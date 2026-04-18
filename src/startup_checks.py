"""Shared startup checks for source and packaged LeetLoop entrypoints."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Iterable


MIN_PYTHON = (3, 10)
MIN_PYTHON_TEXT = "3.10"
REQUIRED_ENV_PLACEHOLDERS = {
    "OPENAI_API_KEY": "your_openai_api_key_here",
    "LEETCODE_SESSION": "your_leetcode_session_here",
    "LEETCODE_CSRFTOKEN": "your_leetcode_csrf_here",
}


def enforce_supported_python() -> None:
    if sys.version_info < MIN_PYTHON:
        print("LeetLoop requires Python 3.10 or newer.")
        raise SystemExit(1)


def required_env_fields() -> tuple[str, ...]:
    return tuple(REQUIRED_ENV_PLACEHOLDERS.keys())


def missing_required_env_vars() -> list[str]:
    missing: list[str] = []
    for key, placeholder in REQUIRED_ENV_PLACEHOLDERS.items():
        value = str(os.environ.get(key, "")).strip()
        if not value or value == placeholder:
            missing.append(key)
    return missing


def setup_command_hint() -> str:
    if platform.system() == "Windows":
        return "Run setup_windows.bat first."
    return "Run ./setup.sh first."


def missing_env_file_message(env_path: Path) -> str:
    return (
        f"Missing .env file at {env_path}.\n"
        f"{setup_command_hint()}"
    )


def missing_credentials_message(missing: Iterable[str], env_path: Path) -> str:
    names = ", ".join(missing)
    return (
        f"Missing required environment variables: {names}\n"
        f"Please update your `{env_path.name}` file and try again."
    )
