#!/usr/bin/env python3
"""LeetLoop launcher for packaged or direct source-style startup."""

from __future__ import annotations

import os
import shutil
import sys
import time
import webbrowser
from pathlib import Path

if sys.version_info < (3, 10):
    print("LeetLoop requires Python 3.10 or newer.")
    raise SystemExit(1)

from dotenv import load_dotenv


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def detect_resource_root() -> Path:
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def detect_app_home(resource_root: Path) -> Path:
    override = os.environ.get("LEETLOOP_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    if not is_frozen():
        return resource_root

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
        return base / "LeetLoop"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "LeetLoop"
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")) / "LeetLoop"


RESOURCE_ROOT = detect_resource_root()
APP_HOME = detect_app_home(RESOURCE_ROOT)
SRC_DIR = RESOURCE_ROOT / "src"

os.environ["LEETLOOP_RESOURCE_ROOT"] = str(RESOURCE_ROOT)
os.environ["LEETLOOP_HOME"] = str(APP_HOME)

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
    validate_startup_environment,
    wait_for_server,
)

ENV_PATH = APP_HOME / ".env"
ENV_TEMPLATE_PATH = RESOURCE_ROOT / ".env.example"


def ensure_runtime_environment() -> None:
    APP_HOME.mkdir(parents=True, exist_ok=True)
    (APP_HOME / "history").mkdir(parents=True, exist_ok=True)

    config_src = RESOURCE_ROOT / "config"
    config_dst = APP_HOME / "config"
    config_dst.mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "app_config.json"):
        src = config_src / name
        dst = config_dst / name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)

    examples_src = RESOURCE_ROOT / "examples"
    examples_dst = APP_HOME / "examples"
    if examples_src.exists():
        examples_dst.mkdir(parents=True, exist_ok=True)
        for child in examples_src.iterdir():
            target = examples_dst / child.name
            if child.is_file() and not target.exists():
                shutil.copy2(child, target)

    if ENV_TEMPLATE_PATH.exists() and not ENV_PATH.exists():
        shutil.copy2(ENV_TEMPLATE_PATH, ENV_PATH)


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
    enforce_supported_python()
    ensure_runtime_environment()

    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)
        missing = missing_required_env_vars()
        if not missing:
            return
        print()
        print(missing_credentials_message(missing, ENV_PATH))
        print()

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
    print(f"Setup complete! Configuration saved to {ENV_PATH}")
    print()


def main() -> None:
    args = set(sys.argv[1:])
    enforce_supported_python()
    ensure_runtime_environment()
    os.chdir(str(APP_HOME))

    if "--run-pipeline" in args:
        load_dotenv(ENV_PATH, override=True)
        from run_pipeline import main as run_pipeline_main
        run_pipeline_main()
        return

    if "--background-agent" in args:
        load_dotenv(ENV_PATH, override=True)
        validate_startup_environment()
        from run_service import run_server
        run_server(background=True)
        return

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
