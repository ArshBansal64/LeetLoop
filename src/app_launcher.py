#!/usr/bin/env python3
"""LeetLoop launcher for packaged or direct source-style startup."""

from __future__ import annotations

import os
import sys
import time
import webbrowser
from pathlib import Path

if sys.version_info < (3, 10):
    print("LeetLoop requires Python 3.10 or newer.")
    raise SystemExit(1)

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from startup_checks import (
    enforce_supported_python,
    missing_credentials_message,
    missing_env_file_message,
    missing_required_env_vars,
    required_env_fields,
)
from run_service import (
    load_app_config,
    port_is_open,
    server_is_running,
    server_url,
    spawn_background_agent,
    stop_recorded_agent,
    wait_for_server,
)

ENV_PATH = PROJECT_ROOT / ".env"
ENV_TEMPLATE_PATH = PROJECT_ROOT / ".env.example"


def write_env_values(values: dict[str, str]) -> None:
    if ENV_PATH.exists():
        content = ENV_PATH.read_text(encoding="utf-8")
    else:
        content = ENV_TEMPLATE_PATH.read_text(encoding="utf-8") if ENV_TEMPLATE_PATH.exists() else ""
    if not content:
        content = (
            "OPENAI_API_KEY=your_openai_api_key_here\n"
            "OPENAI_MODEL=gpt-5.4\n"
            "LEETCODE_SESSION=your_leetcode_session_here\n"
            "LEETCODE_CSRFTOKEN=your_leetcode_csrf_here\n"
        )

    for key, replacement_value in values.items():
        lines = content.splitlines()
        replaced = False
        for idx, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[idx] = f"{key}={replacement_value}"
                replaced = True
                break
        if not replaced:
            lines.append(f"{key}={replacement_value}")
        content = "\n".join(lines) + "\n"

    ENV_PATH.write_text(content, encoding="utf-8")


def setup_env_first_run() -> None:
    """Prompt for all required credentials before launching."""
    enforce_supported_python()

    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)
        missing = missing_required_env_vars()
        if not missing:
            return
        print()
        print(missing_credentials_message(missing, ENV_PATH))
        print()
    elif ENV_TEMPLATE_PATH.exists():
        ENV_PATH.write_text(ENV_TEMPLATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    print()
    print("=" * 60)
    print("LeetLoop - First Time Setup")
    print("=" * 60)
    print()
    print("You need these credentials to finish setup:")
    print("  - OPENAI_API_KEY")
    print("  - LEETCODE_SESSION")
    print("  - LEETCODE_CSRFTOKEN")
    print()
    print("OpenAI API key: https://platform.openai.com/api-keys")
    print("LeetCode cookies: sign in on https://leetcode.com, then open Developer Tools -> Application/Storage -> Cookies -> https://leetcode.com")
    print()

    prompts = {
        "OPENAI_API_KEY": "Enter your OpenAI API key",
        "LEETCODE_SESSION": "Enter your LEETCODE_SESSION value",
        "LEETCODE_CSRFTOKEN": "Enter your LEETCODE_CSRFTOKEN value",
    }
    values: dict[str, str] = {}
    for key in required_env_fields():
        value = input(f"{prompts[key]}: ").strip()
        if not value:
            print(f"\nSetup cancelled - {key} is required.")
            raise SystemExit(1)
        values[key] = value

    write_env_values(values)
    load_dotenv(ENV_PATH, override=True)

    missing = missing_required_env_vars()
    if missing:
        print()
        print(missing_credentials_message(missing, ENV_PATH))
        raise SystemExit(1)

    print()
    print("Setup complete! Configuration saved to .env")
    print()


def main() -> None:
    """Main launcher entry point."""
    enforce_supported_python()
    os.chdir(str(PROJECT_ROOT))

    setup_env_first_run()

    if not ENV_PATH.exists():
        print(missing_env_file_message(ENV_PATH))
        raise SystemExit(1)

    load_dotenv(ENV_PATH, override=True)
    missing = missing_required_env_vars()
    if missing:
        print(missing_credentials_message(missing, ENV_PATH))
        raise SystemExit(1)

    config = load_app_config()
    url = server_url(config)

    print()
    print("=" * 60)
    print("LeetLoop")
    print("=" * 60)
    print()

    if server_is_running(config):
        print(f"LeetLoop is already running at {url}")
        webbrowser.open(url)
        return

    if port_is_open(config):
        print("Stopping stale background service...")
        stop_recorded_agent()
        time.sleep(2)

    print("Starting LeetLoop background service...")
    spawn_background_agent()

    if not wait_for_server():
        print("Failed to start LeetLoop service.")
        raise SystemExit(1)

    print(f"Service started successfully. Opening: {url}")
    webbrowser.open(url)

    print()
    print("LeetLoop is running in the background.")
    print("Close this window when you're done, or press Ctrl+C.")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down LeetLoop...")
        stop_recorded_agent()
        raise SystemExit(0)


if __name__ == "__main__":
    main()
