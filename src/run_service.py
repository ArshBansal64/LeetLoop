import datetime
import html
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
import socket
import platform
import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen
from urllib.error import URLError
import signal

if sys.version_info < (3, 10):
    print("LeetLoop requires Python 3.10 or newer.")
    raise SystemExit(1)

from dotenv import load_dotenv
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from startup_checks import (
    enforce_supported_python,
    missing_credentials_message,
    missing_env_file_message,
    missing_required_env_vars,
)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.environ.get("LEETLOOP_HOME") or BASE_DIR.parent).resolve()
RESOURCE_ROOT = Path(os.environ.get("LEETLOOP_RESOURCE_ROOT") or PROJECT_ROOT).resolve()
ENV_PATH = PROJECT_ROOT / ".env"
HISTORY_DIR = PROJECT_ROOT / "history"
CONFIG_DIR = PROJECT_ROOT / "config"
APP_CONFIG_PATH = CONFIG_DIR / "app_config.json"
PLANNER_CONFIG_PATH = CONFIG_DIR / "config.json"
AGENT_PID_PATH = CONFIG_DIR / "agent.pid"

load_dotenv(dotenv_path=ENV_PATH)

DEFAULT_APP_CONFIG = {
    "host": "127.0.0.1",
    "port": 8765,
    "daily_time": "",
    "open_browser_on_start": True,
    "scheduled_retry_attempts": 3,
    "scheduled_retry_delay_seconds": 300,
}

DEFAULT_TIMEZONE = "America/Los_Angeles"
TIMEZONE_OPTIONS = [
    "UTC",
    "America/Los_Angeles",
    "America/Denver",
    "America/Phoenix",
    "America/Chicago",
    "America/New_York",
    "Europe/London",
    "Europe/Berlin",
    "Asia/Kolkata",
    "Asia/Singapore",
    "Asia/Tokyo",
    "Australia/Sydney",
]

PLANNING_MODE_OPTIONS = {
    "balanced_growth": "Balanced Growth (2 review, 2 gap-fill)",
    "interview_maintenance": "Interview Maintenance (3 review, 1 gap-fill)",
    "aggressive_gap_fill": "Aggressive Gap Fill (1 review, 3 gap-fill)",
}

state_lock = threading.Lock()
service_state = {
    "is_running": False,
    "last_status": "idle",
    "last_message": "Service started.",
    "last_started_at": None,
    "last_finished_at": None,
    "last_run_dir": None,
    "last_run_date": None,
    "last_scheduled_date": None,
    "progress_step_index": 0,
    "progress_step_total": 0,
    "progress_label": "",
    "progress_percent": 0,
    "last_detail": "",
    "progress_history": [],
}


ACTIVE_SERVER = None


def safe_zoneinfo(name: str) -> datetime.tzinfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return datetime.UTC


def current_timezone_name() -> str:
    config = load_planner_config()
    candidate = str(config.get("timezone") or DEFAULT_TIMEZONE).strip()
    try:
        ZoneInfo(candidate)
        return candidate
    except ZoneInfoNotFoundError:
        try:
            ZoneInfo(DEFAULT_TIMEZONE)
            return DEFAULT_TIMEZONE
        except ZoneInfoNotFoundError:
            return "UTC"


def current_timezone() -> datetime.tzinfo:
    return safe_zoneinfo(current_timezone_name())


def now_local_iso() -> str:
    return datetime.datetime.now(datetime.UTC).astimezone(current_timezone()).isoformat(timespec="seconds")


def format_saved_iso(dt_str: str | None) -> str:
    if not dt_str:
        return "Never"
    try:
        dt = datetime.datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
        return dt.astimezone(current_timezone()).strftime("%b %d, %Y %I:%M:%S %p %Z")
    except Exception:
        return str(dt_str)


def timezone_options_html(selected_timezone: str) -> str:
    values = list(TIMEZONE_OPTIONS)
    if selected_timezone not in values:
        values.append(selected_timezone)
    parts = []
    for value in values:
        selected = ' selected' if value == selected_timezone else ''
        parts.append(f'<option value="{html.escape(value)}"{selected}>{html.escape(value)}</option>')
    return ''.join(parts)


def load_json(path: Path, default):
    if path.exists():
        try:
            content = path.read_text(encoding="utf-8").strip()
            if not content:
                return default
            return json.loads(content)
        except (json.JSONDecodeError, IOError):
            return default
    return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_app_config():
    config = dict(DEFAULT_APP_CONFIG)
    config.update(load_json(APP_CONFIG_PATH, {}))
    save_json(APP_CONFIG_PATH, config)
    return config


def save_app_config(config):
    merged = dict(DEFAULT_APP_CONFIG)
    merged.update(config)
    save_json(APP_CONFIG_PATH, merged)


def load_planner_config():
    return load_json(PLANNER_CONFIG_PATH, {})


def save_planner_config(config):
    save_json(PLANNER_CONFIG_PATH, config)


def validate_startup_environment() -> None:
    enforce_supported_python()
    if not ENV_PATH.exists():
        raise RuntimeError(missing_env_file_message(ENV_PATH))

    missing = missing_required_env_vars()
    if missing:
        raise RuntimeError(missing_credentials_message(missing, ENV_PATH))


def run_setup_check() -> int:
    enforce_supported_python()
    print(f"Python version: {sys.version.split()[0]}")
    print(f".env file exists: {ENV_PATH.exists()}")

    missing = missing_required_env_vars()
    for key in ("OPENAI_API_KEY", "LEETCODE_SESSION", "LEETCODE_CSRFTOKEN"):
        print(f"{key} present: {key not in missing}")

    for path in (PLANNER_CONFIG_PATH, APP_CONFIG_PATH):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            print(f"Config load OK: {path.relative_to(PROJECT_ROOT)}")
        except Exception as exc:
            print(f"Config load failed: {path.relative_to(PROJECT_ROOT)} ({exc})")
            return 1

    if not ENV_PATH.exists():
        print(missing_env_file_message(ENV_PATH))
        return 1
    if missing:
        print(missing_credentials_message(missing, ENV_PATH))
        return 1

    print("LeetLoop setup looks valid.")
    return 0


def current_planning_bias() -> str:
    config = load_planner_config()
    bias = str(config.get("planning_bias", "balanced_growth"))
    return bias if bias in PLANNING_MODE_OPTIONS else "balanced_growth"


def list_run_dirs():
    if not HISTORY_DIR.exists():
        return []
    # Sort by directory name (timestamp format YYYY-MM-DD_HH-MM-SS sorts correctly as strings)
    dirs = [p for p in HISTORY_DIR.iterdir() if p.is_dir()]
    return sorted(dirs, key=lambda p: p.name)


def latest_run_dir():
    dirs = list_run_dirs()
    return dirs[-1] if dirs else None


def resolve_run_dir(run_name: str | None):
    dirs = list_run_dirs()
    if not dirs:
        return None
    if run_name:
        for run_dir in dirs:
            if run_dir.name == run_name:
                return run_dir
    return dirs[-1]


def load_artifacts_for_run(run_dir: Path | None):
    if not run_dir:
        return None, None, None
    recommendation = load_json(run_dir / "recommendation.json", {})
    buckets = load_json(run_dir / "candidate_buckets.json", {})
    return run_dir, recommendation, buckets


def load_latest_artifacts():
    return load_artifacts_for_run(latest_run_dir())


def infer_last_run_date_from_history():
    run_dir = latest_run_dir()
    if not run_dir:
        return None
    parts = run_dir.name.split("_")
    return parts[0] if parts else None


def validate_daily_time(value: str) -> bool:
    try:
        datetime.datetime.strptime(value, "%H:%M")
        return True
    except ValueError:
        return False


def extract_planner_failure_message(stdout: str, stderr: str, recommendation_exists: bool, created_new_run: bool = True) -> str:
    combined = "\n".join(part for part in [stderr, stdout] if part).strip()
    if not created_new_run:
        return "Planner exited without creating a new history folder. Check the run details below."
    if not combined and not recommendation_exists:
        return "Planner run did not produce recommendation.json."

    match = re.search(r"Pipeline failed\.\s*(.+)", combined, re.DOTALL)
    if match:
        message = match.group(1).strip().splitlines()[0].strip()
        if message:
            return message

    lowered = combined.lower()
    if "no available balance" in lowered or "no available quota" in lowered or "insufficient balance" in lowered or "insufficient quota" in lowered:
        return "OpenAI account has no available balance or quota. Add billing or credits, then rerun the planner."
    if "api key was rejected" in lowered or "invalid_api_key" in lowered:
        return "OpenAI API key was rejected. Check OPENAI_API_KEY and rerun the planner."

    for line in [line.strip() for line in combined.splitlines() if line.strip()]:
        if line.startswith("OpenAI") or line.startswith("LeetCode"):
            return line
        if line.startswith("Pipeline failed"):
            continue

    return combined.splitlines()[0].strip() if combined else "Planner failed."


def parse_progress_line(line: str):
    match = re.match(r"\[PROGRESS\s+(\d+)/(\d+)\]\s+(.+)", line.strip())
    if not match:
        return None
    step_index = int(match.group(1))
    step_total = int(match.group(2))
    label = match.group(3).strip()
    percent = int((step_index / step_total) * 100) if step_total else 0
    return {
        "step_index": step_index,
        "step_total": step_total,
        "label": label,
        "percent": percent,
    }


def apply_progress_update(progress: dict):
    with state_lock:
        service_state["progress_step_index"] = progress["step_index"]
        service_state["progress_step_total"] = progress["step_total"]
        service_state["progress_label"] = progress["label"]
        service_state["progress_percent"] = progress["percent"]
        service_state["last_message"] = f"{progress['step_index']}/{progress['step_total']} - {progress['label']}"
        history = list(service_state.get("progress_history") or [])
        entry = f"{progress['step_index']}/{progress['step_total']} - {progress['label']}"
        if not history or history[-1] != entry:
            history.append(entry)
        service_state["progress_history"] = history[-12:]


def summarize_run_detail(stdout: str, stderr: str) -> str:
    lines = [line.strip() for line in (stderr + "\n" + stdout).splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-12:])


def trigger_run(reason: str = "manual") -> bool:
    with state_lock:
        if service_state["is_running"]:
            return False
        service_state["is_running"] = True
        service_state["last_status"] = "running"
        service_state["last_message"] = f"Planner started via {reason}."
        service_state["last_started_at"] = now_local_iso()
        service_state["progress_step_index"] = 0
        service_state["progress_step_total"] = 0
        service_state["progress_label"] = "Starting planner"
        service_state["progress_percent"] = 5
        service_state["last_detail"] = ""
        service_state["progress_history"] = []

    thread = threading.Thread(target=run_pipeline_job, args=(reason,), daemon=True)
    thread.start()
    return True


def run_pipeline_job(reason: str):
    env = os.environ.copy()
    env["LEETLOOP_OPEN_BROWSER"] = "0"
    cmd = planner_command()
    app_config = load_app_config()
    attempt_total = int(app_config.get("scheduled_retry_attempts", 3)) if reason == "schedule" else 1
    attempt_total = max(1, attempt_total)
    retry_delay_seconds = int(app_config.get("scheduled_retry_delay_seconds", 300)) if reason == "schedule" else 0
    retry_delay_seconds = max(0, retry_delay_seconds)

    last_stdout = ""
    last_stderr = ""
    last_detail = ""
    last_latest_name = latest_run_dir().name if latest_run_dir() else None
    last_recommendation_exists = False
    last_created_new_run = False
    last_return_code = 1

    try:
        for attempt_index in range(1, attempt_total + 1):
            start_latest = latest_run_dir()
            start_latest_name = start_latest.name if start_latest else None

            with state_lock:
                service_state["progress_label"] = f"Attempt {attempt_index}/{attempt_total}"
                service_state["last_message"] = f"Running planner attempt {attempt_index}/{attempt_total} via {reason}."
                service_state["progress_percent"] = max(int(service_state.get("progress_percent", 0) or 0), 5)

            process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            stdout_lines = []
            if process.stdout is not None:
                for raw_line in process.stdout:
                    line = raw_line.rstrip()
                    stdout_lines.append(line)
                    progress = parse_progress_line(line)
                    if progress:
                        apply_progress_update(progress)

            stderr_text = process.stderr.read().strip() if process.stderr is not None else ""
            return_code = process.wait(timeout=900)
            stdout = "\n".join(stdout_lines).strip()
            stderr = stderr_text
            
            # Small delay to ensure filesystem has flushed
            time.sleep(0.5)
            
            latest = latest_run_dir()
            latest_name = latest.name if latest else None
            created_new_run = bool(latest_name and latest_name != start_latest_name)
            recommendation_exists = False
            
            # Try to find recommendation.json with retry for filesystem sync
            if created_new_run and latest:
                for _ in range(5):  # Retry up to 5 times with 100ms delay
                    if (latest / "recommendation.json").exists():
                        recommendation_exists = True
                        break
                    time.sleep(0.1)
            elif latest:
                # Even if no new run folder, check if latest has recommendation
                if (latest / "recommendation.json").exists():
                    recommendation_exists = True
                    created_new_run = True  # Treat as success if file exists
            
            detail = summarize_run_detail(stdout, stderr)

            last_stdout = stdout
            last_stderr = stderr
            last_detail = detail
            last_latest_name = latest_name
            last_recommendation_exists = recommendation_exists
            last_created_new_run = created_new_run
            last_return_code = return_code

            if return_code == 0 and created_new_run and recommendation_exists:
                with state_lock:
                    service_state["is_running"] = False
                    service_state["last_finished_at"] = now_local_iso()
                    service_state["last_run_dir"] = latest_name
                    service_state["last_detail"] = detail
                    service_state["last_status"] = "ok"
                    service_state["last_message"] = f"Planner finished successfully via {reason}."
                    service_state["progress_step_index"] = max(service_state.get("progress_step_index", 0), 6)
                    service_state["progress_step_total"] = max(service_state.get("progress_step_total", 0), 6)
                    service_state["progress_label"] = "Completed"
                    service_state["progress_percent"] = 100
                    service_state["progress_history"] = list(service_state.get("progress_history") or [])
                    if latest_name:
                        service_state["last_run_date"] = latest_name.split("_")[0]
                    if reason == "schedule":
                        service_state["last_scheduled_date"] = datetime.datetime.now(datetime.UTC).astimezone(current_timezone()).date().isoformat()
                return

            if attempt_index < attempt_total:
                failure_message = extract_planner_failure_message(
                    stdout=stdout,
                    stderr=stderr,
                    recommendation_exists=recommendation_exists,
                    created_new_run=created_new_run,
                )
                with state_lock:
                    service_state["last_detail"] = detail
                    service_state["last_status"] = "running"
                    service_state["progress_label"] = f"Retrying in {retry_delay_seconds}s"
                    service_state["last_message"] = f"Attempt {attempt_index}/{attempt_total} failed: {failure_message} Retrying in {retry_delay_seconds}s."
                    service_state["progress_percent"] = min(int(service_state.get("progress_percent", 0) or 0), 95)
                    service_state["progress_history"] = list(service_state.get("progress_history") or [])
                time.sleep(retry_delay_seconds)

        with state_lock:
            service_state["is_running"] = False
            service_state["last_finished_at"] = now_local_iso()
            service_state["last_run_dir"] = last_latest_name
            service_state["last_detail"] = last_detail
            service_state["last_status"] = "error"
            service_state["last_message"] = extract_planner_failure_message(
                stdout=last_stdout,
                stderr=last_stderr,
                recommendation_exists=last_recommendation_exists,
                created_new_run=last_created_new_run,
            )
            service_state["progress_label"] = "Failed"
            service_state["progress_percent"] = min(int(service_state.get("progress_percent", 0) or 0), 95)
    except Exception as exc:
        with state_lock:
            service_state["is_running"] = False
            service_state["last_finished_at"] = now_local_iso()
            service_state["last_status"] = "error"
            service_state["last_message"] = f"Service error: {exc}"
            service_state["last_detail"] = str(exc)

def title_to_slug(title: str) -> str:
    """Convert question title to LeetCode slug format"""
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def normalize_plan_title(title: str) -> str:
    value = re.sub(r"^\d+\.\s*", "", str(title or "").strip())
    value = re.sub(r"^(Redo|Learn)\s+", "", value, flags=re.IGNORECASE)
    return value.rstrip(".").strip().lower()


def infer_badge_from_action_text(task_text: str, action_text: str) -> tuple[str, str] | None:
    normalized = normalize_plan_title(task_text)
    if not normalized:
        return None

    for raw_line in str(action_text or "").splitlines():
        line = re.sub(r"^\d+\.\s*", "", raw_line.strip())
        if not line:
            continue
        lowered = line.lower()
        candidate = normalize_plan_title(line)
        if candidate != normalized:
            continue
        if lowered.startswith("redo "):
            return ("task-redo", "Review")
        if lowered.startswith("learn "):
            return ("task-learn", "Learn")
        if "review" in lowered:
            return ("task-redo", "Review")
        if "learn" in lowered:
            return ("task-learn", "Learn")
    return None


def infer_item_badge(
    task_text: str,
    primary_action: str | None = None,
    secondary_action: str | None = None,
    stretch_action: str | None = None,
) -> tuple[str, str]:
    for action_text in (primary_action, secondary_action, stretch_action):
        inferred = infer_badge_from_action_text(task_text, str(action_text or ""))
        if inferred:
            return inferred

    return ("task-generic", "Task")


def parse_plan_items(
    tldr: str | None,
    problem_metadata: dict | None = None,
    problem_reasons: list[str] | None = None,
    primary_action: str | None = None,
    secondary_action: str | None = None,
    stretch_action: str | None = None,
) -> list[dict[str, str]]:
    problem_metadata = problem_metadata or {}
    raw_lines = [line.strip() for line in str(tldr or "").splitlines() if line.strip()]
    items: list[dict[str, str]] = []

    for raw_line in raw_lines:
        line = re.sub(r"^\d+\.\s*", "", raw_line).strip()
        css = "task-generic"
        badge = "Task"
        task_text = line

        if line.startswith("Redo "):
            css = "task-redo"
            badge = "Review"
            task_text = line[len("Redo "):].strip()
        elif line.startswith("Learn "):
            css = "task-learn"
            badge = "Learn"
            task_text = line[len("Learn "):].strip()

        task_text = task_text.rstrip(".")
        if task_text:
            if badge == "Task":
                css, badge = infer_item_badge(
                    task_text,
                    primary_action=primary_action,
                    secondary_action=secondary_action,
                    stretch_action=stretch_action,
                )
            items.append({
                "css": css,
                "badge": badge,
                "name": task_text,
            })

    # Handle single-sentence TLDRs like:
    # "Do these 4 in order: A, B, C, D."
    if len(items) == 1:
        single_name = items[0]["name"]
        intro_match = re.match(r"^(?:do|solve|work on)\b.+?:\s*(.+)$", single_name, flags=re.IGNORECASE)
        if intro_match:
            split_parts = [part.strip().rstrip(".") for part in intro_match.group(1).split(",") if part.strip()]
            matched_parts = [part for part in split_parts if part in problem_metadata]
            if problem_reasons:
                reason_titles = []
                for reason in problem_reasons:
                    match = re.match(r"^\s*(.+?)\s*:", str(reason).strip())
                    if match:
                        reason_titles.append(match.group(1).strip())
                if reason_titles:
                    split_parts = reason_titles
                    matched_parts = reason_titles
            if len(matched_parts) >= 2:
                items = []
                for part in split_parts:
                    inferred_css, inferred_badge = infer_item_badge(
                        part,
                        primary_action=primary_action,
                        secondary_action=secondary_action,
                        stretch_action=stretch_action,
                    )
                    items.append({
                        "css": inferred_css,
                        "badge": inferred_badge,
                        "name": part,
                    })

    # Final fallback: derive ordered tasks from problem reasons when TLDR is not structured enough.
    if len(items) <= 1 and problem_reasons:
        derived_items = []
        for reason in problem_reasons:
            match = re.match(r"^\s*(.+?)\s*:", str(reason).strip())
            if not match:
                continue
            title = match.group(1).strip().rstrip(".")
            if title:
                inferred_css, inferred_badge = infer_item_badge(
                    title,
                    primary_action=primary_action,
                    secondary_action=secondary_action,
                    stretch_action=stretch_action,
                )
                derived_items.append({
                    "css": inferred_css,
                    "badge": inferred_badge,
                    "name": title,
                })
        if len(derived_items) >= 2:
            items = derived_items

    return items


def format_plan_html(
    tldr: str,
    problem_metadata: dict | None = None,
    problem_reasons: list[str] | None = None,
    primary_action: str | None = None,
    secondary_action: str | None = None,
    stretch_action: str | None = None,
) -> str:
    items_data = parse_plan_items(
        tldr,
        problem_metadata,
        problem_reasons,
        primary_action,
        secondary_action,
        stretch_action,
    )
    if not items_data:
        return '<div class="plan-empty">No recommendation yet.</div>'

    problem_metadata = problem_metadata or {}
    items = []
    for item in items_data:
        css = item["css"]
        badge = item["badge"]
        task_text = item["name"]

        problem_content = html.escape(task_text)
        problem_data = problem_metadata.get(task_text)
        if problem_data:
            slug = problem_data.get("slug", title_to_slug(task_text))
            frontend_id = problem_data.get("frontend_id", "")
            display_text = f"{frontend_id}: {task_text}" if frontend_id else task_text
            leetcode_url = f"https://leetcode.com/problems/{slug}/"
            leetcode_icon = '<svg class="leetcode-icon" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M7 17L17 7M17 7H9M17 7V15" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            problem_content = (
                f'<a href="{html.escape(leetcode_url)}" target="_blank" class="plan-link {css}">'
                f'<span class="task-badge">{html.escape(badge)}</span>'
                f'<span class="task-text">{html.escape(display_text)}{leetcode_icon}</span>'
                f'</a>'
            )
            items.append(f'<li class="plan-item plan-item-clickable {css}">{problem_content}</li>')
        else:
            items.append(
                f'<li class="plan-item {css}"><span class="task-badge">{html.escape(badge)}</span><span class="task-text">{problem_content}</span></li>'
            )

    return '<ol class="plan-list">' + ''.join(items) + '</ol>'


def format_why_now_html(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return '<p class="why-paragraph">Run the planner to generate a recommendation.</p>'

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", value) if s.strip()]
    if not sentences:
        return f'<p class="why-paragraph">{html.escape(value)}</p>'

    return ''.join(f'<p class="why-paragraph">{html.escape(sentence)}</p>' for sentence in sentences)


def format_problem_reasons_html(
    reasons,
    tldr: str | None = None,
    problem_metadata: dict | None = None,
    primary_action: str | None = None,
    secondary_action: str | None = None,
    stretch_action: str | None = None,
) -> str:
    reasons = [str(x).strip() for x in (reasons or []) if str(x).strip()]
    if not reasons:
        return '<div class="problem-reasons-empty">No problem-specific explanation yet.</div>'

    problems_info = [
        {
            "type": item["badge"].lower(),
            "badge": item["badge"],
            "name": item["name"],
        }
        for item in parse_plan_items(
            tldr,
            problem_metadata,
            reasons,
            primary_action,
            secondary_action,
            stretch_action,
        )
    ]

    # Build items with just problem index + badge + explanation (no name redundancy)
    items = []
    problem_metadata = problem_metadata or {}
    
    for idx, reason in enumerate(reasons):
        if idx < len(problems_info):
            prob = problems_info[idx]
            
            # Try to create a link for the number if we have metadata
            prob_data = problem_metadata.get(prob["name"])
            number_class = f"problem-number problem-number-{prob['type']}"
            if prob_data:
                frontend_id = prob_data.get("frontend_id", "")
                slug = prob_data.get("slug", title_to_slug(prob["name"]))
                leetcode_url = f"https://leetcode.com/problems/{slug}/"
                prob_number_html = f'<a href="{html.escape(leetcode_url)}" target="_blank" class="{number_class}" style="text-decoration: underline;">{frontend_id}</a>'
            else:
                prob_number_html = f'<span class="{number_class}">?</span>'
            
            items.append(
                f'<div class="problem-reason-item">{prob_number_html}: {html.escape(reason)}</div>'
            )
        else:
            items.append(f'<div class="problem-reason-item">{html.escape(reason)}</div>')
    
    return f'<div class="problem-reasons">{"".join(items)}</div>'


def planning_mode_options_html(selected_bias: str) -> str:
    parts = []
    for value, label in PLANNING_MODE_OPTIONS.items():
        selected = ' selected' if value == selected_bias else ''
        parts.append(f'<option value="{html.escape(value)}"{selected}>{html.escape(label)}</option>')
    return ''.join(parts)


def build_run_query(run_name: str | None) -> str:
    if not run_name:
        return '/'
    return f'/?run={html.escape(run_name)}'


def format_run_label(run_name: str) -> str:
    run_dir = HISTORY_DIR / run_name
    recommendation = load_json(run_dir / "recommendation.json", {}) if run_dir.exists() else {}
    generated_at = recommendation.get("generated_at")
    if generated_at:
        try:
            dt = datetime.datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
            return dt.astimezone(current_timezone()).strftime("%b %d, %Y\n%I:%M %p %Z")
        except Exception:
            pass
    try:
        dt = datetime.datetime.strptime(run_name, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=current_timezone())
        return dt.strftime("%b %d, %Y\n%I:%M %p %Z")
    except ValueError:
        return run_name


def history_timeline_html(run_dirs, selected_run_name: str | None) -> str:
    # Only show runs that have a valid recommendation.json (complete runs)
    complete_runs = [run_dir for run_dir in run_dirs if (run_dir / "recommendation.json").exists()]
    
    if not complete_runs:
        return '<div class="timeline-empty">No completed runs yet.</div>'

    items = []
    for run_dir in reversed(complete_runs):
        name = run_dir.name
        selected = name == selected_run_name
        classes = 'timeline-item is-selected' if selected else 'timeline-item'
        marker = 'Current' if selected else 'View'
        items.append(
            f'<a class="{classes}" href="{build_run_query(name)}">'
            f'<span class="timeline-dot"></span>'
            f'<span class="timeline-copy">'
            f'<span class="timeline-date">{html.escape(format_run_label(name))}</span>'
            f'<span class="timeline-id mono">{html.escape(name)}</span>'
            f'</span>'
            f'<span class="timeline-tag">{html.escape(marker)}</span>'
            f'</a>'
        )
    return '<div class="timeline">' + ''.join(items) + '</div>'



def server_url(config=None) -> str:
    cfg = config or load_app_config()
    return f"http://{cfg['host']}:{int(cfg['port'])}/"


def health_url(config=None) -> str:
    return server_url(config).rstrip("/") + "/health"


def port_is_open(config=None) -> bool:
    cfg = config or load_app_config()
    host = cfg["host"]
    port = int(cfg["port"])
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.4)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def server_is_running(config=None) -> bool:
    try:
        with urlopen(health_url(config), timeout=0.8) as response:
            return response.status == 200 and response.read().decode("utf-8").strip() == "ok"
    except Exception:
        return False


def read_agent_pid() -> int | None:
    try:
        value = AGENT_PID_PATH.read_text(encoding="utf-8").strip()
        return int(value) if value else None
    except Exception:
        return None


def write_agent_pid() -> None:
    AGENT_PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    AGENT_PID_PATH.write_text(str(os.getpid()), encoding="utf-8")


def clear_agent_pid() -> None:
    try:
        if AGENT_PID_PATH.exists():
            AGENT_PID_PATH.unlink()
    except Exception:
        pass


def stop_recorded_agent() -> bool:
    pid = read_agent_pid()
    if not pid:
        return False
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(pid, signal.SIGTERM)
        return True
    except Exception:
        return False


def process_ids_on_port(config=None) -> list[int]:
    cfg = config or load_app_config()
    port = int(cfg["port"])
    pids: set[int] = set()
    try:
        if platform.system() == "Windows":
            result = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, check=False)
            for line in result.stdout.splitlines():
                if f":{port}" not in line:
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        pid = int(parts[-1])
                        if pid > 0:
                            pids.add(pid)
                    except ValueError:
                        pass
        else:
            result = subprocess.run(["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True, check=False)
            for line in result.stdout.splitlines():
                try:
                    pid = int(line.strip())
                    if pid > 0:
                        pids.add(pid)
                except ValueError:
                    pass
    except Exception:
        return []
    return sorted(pids)


def stop_processes_on_port(config=None) -> bool:
    pids = process_ids_on_port(config)
    if not pids:
        return False
    stopped = False
    for pid in pids:
        try:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                os.kill(pid, signal.SIGTERM)
            stopped = True
        except Exception:
            pass
    return stopped


def background_python_executable() -> str:
    if os.name == "nt":
        exe = Path(sys.executable)
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            return str(pythonw)
    return sys.executable


def running_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def launcher_executable() -> str:
    return sys.executable


def planner_command() -> list[str]:
    if running_frozen():
        return [launcher_executable(), "--run-pipeline"]
    return [sys.executable, str(BASE_DIR / "run_pipeline.py")]


def background_command() -> list[str]:
    if running_frozen():
        return [launcher_executable(), "--background-agent"]
    return [background_python_executable(), str(BASE_DIR / "run_service.py"), "--background"]


def spawn_background_agent() -> None:
    cmd = background_command()
    kwargs = {"cwd": str(PROJECT_ROOT)}
    
    # Create log file for background process
    log_file = PROJECT_ROOT / "background_agent.log"
    try:
        with open(log_file, "w") as f:
            f.write(f"Background agent started at {datetime.datetime.now().isoformat()}\n")
    except:
        pass
    
    try:
        log_handle = open(log_file, "a")
    except:
        log_handle = subprocess.DEVNULL
    
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 7  # SW_SHOWMINNOACTIVE
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, stdout=log_handle, stderr=log_handle, **kwargs)


def wait_for_server(timeout_seconds: float = 8.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if server_is_running():
            return True
        time.sleep(0.2)
    return False


def startup_file_windows() -> Path:
    return Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "LeetLoopAgent.bat"


def startup_file_macos() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / "com.leetloop.agent.plist"



def autostart_enabled() -> bool:
    system = platform.system()
    if system == "Windows":
        return startup_file_windows().exists()
    if system == "Darwin":
        return startup_file_macos().exists()
    return False


def install_autostart() -> str:
    python_path = background_python_executable()
    script_path = str(BASE_DIR / "run_service.py")
    system = platform.system()
    if system == "Windows":
        target = startup_file_windows()
        target.parent.mkdir(parents=True, exist_ok=True)
        if running_frozen():
            target.write_text(
                f'@echo off\ncd /d "{PROJECT_ROOT}"\n"{launcher_executable()}" --background-agent\n',
                encoding='utf-8',
            )
        else:
            target.write_text(
                f'@echo off\ncd /d "{PROJECT_ROOT}"\n"{python_path}" "{script_path}" --background\n',
                encoding='utf-8',
            )
        return f"Launch at login enabled via {target}"
    if system == "Darwin":
        target = startup_file_macos()
        target.parent.mkdir(parents=True, exist_ok=True)
        if running_frozen():
            program_args = (
                f'    <string>{launcher_executable()}</string>\n'
                '    <string>--background-agent</string>\n'
            )
        else:
            program_args = (
                f'    <string>{python_path}</string>\n'
                f'    <string>{script_path}</string>\n'
                '    <string>--background</string>\n'
            )
        plist = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n'
            '<dict>\n'
            '  <key>Label</key><string>com.leetloop.agent</string>\n'
            '  <key>ProgramArguments</key>\n'
            '  <array>\n'
            f'{program_args}'
            '  </array>\n'
            f'  <key>WorkingDirectory</key><string>{PROJECT_ROOT}</string>\n'
            '  <key>RunAtLoad</key><true/>\n'
            '  <key>KeepAlive</key><true/>\n'
            '</dict>\n'
            '</plist>\n'
        )
        target.write_text(plist, encoding='utf-8')
        return f"Launch at login enabled via {target}"
    return "Launch at login is currently supported on Windows and macOS only."


def uninstall_autostart() -> str:
    system = platform.system()
    targets = [startup_file_windows()] if system == "Windows" else [startup_file_macos()] if system == "Darwin" else []
    removed = False
    for target in targets:
        if target.exists():
            target.unlink()
            removed = True
    return "Launch at login disabled." if removed else "Launch at login was not enabled."


def launch_mode_label() -> str:
    return "Enabled" if autostart_enabled() else "Disabled"


def build_page(selected_run_name: str | None = None):
    config = load_app_config()
    planner_bias = current_planning_bias()
    run_dirs = list_run_dirs()
    selected_run_dir = resolve_run_dir(selected_run_name)
    run_dir, recommendation, buckets = load_artifacts_for_run(selected_run_dir)

    with state_lock:
        snapshot = dict(service_state)

    run_id = recommendation.get("run_id", "No runs yet") if recommendation else "No runs yet"
    tldr = recommendation.get("tldr", "No recommendation yet.") if recommendation else "No recommendation yet."
    why_now = recommendation.get("why_now_summary") or recommendation.get("why_now", "Run the planner to generate a recommendation.") if recommendation else "Run the planner to generate a recommendation."
    problem_reasons = recommendation.get("problem_reasons", []) if recommendation else []
    focus_mode = recommendation.get("focus_mode", "unknown") if recommendation else "unknown"
    confidence = recommendation.get("confidence", "unknown") if recommendation else "unknown"
    target_shape = (((buckets or {}).get("target_shape")) or {})
    problem_metadata = recommendation.get("problem_metadata", {}) if recommendation else {}
    primary_action = recommendation.get("primary_action", "") if recommendation else ""
    secondary_action = recommendation.get("secondary_action", "") if recommendation else ""
    stretch_action = recommendation.get("stretch_action", "") if recommendation else ""

    selected_run_name = run_dir.name if run_dir else None
    run_names = [p.name for p in run_dirs]
    selected_index = run_names.index(selected_run_name) if selected_run_name in run_names else -1
    newer_run_name = run_names[selected_index + 1] if selected_index != -1 and selected_index < len(run_names) - 1 else None
    older_run_name = run_names[selected_index - 1] if selected_index > 0 else None

    plan_html = format_plan_html(
        tldr,
        problem_metadata,
        problem_reasons,
        primary_action,
        secondary_action,
        stretch_action,
    )
    why_html = format_why_now_html(why_now)
    problem_reasons_html = format_problem_reasons_html(
        problem_reasons,
        tldr,
        problem_metadata,
        primary_action,
        secondary_action,
        stretch_action,
    )
    timezone_name = current_timezone_name()
    mode_options = planning_mode_options_html(planner_bias)
    timezone_options = timezone_options_html(timezone_name)
    history_timeline = history_timeline_html(run_dirs, selected_run_name)
    next_run = f"Every day at {config['daily_time']} {timezone_name}" if config['daily_time'] else "Not scheduled"
    autostart_label = launch_mode_label()
    progress_history_items = "".join(f"<li>{html.escape(str(item))}</li>" for item in (snapshot.get("progress_history") or [])[:-1])

    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LeetLoop</title>
  <style>
    :root {{
      --bg: #f3efe7;
      --panel: #fffdf8;
      --ink: #1d1a16;
      --muted: #6f665d;
      --line: #d8cfc4;
      --accent: #17594a;
      --accent-soft: #e3f0ec;
      --warn: #8d4b2b;
      --review: #1d5f8c;
      --review-soft: #e4f1fa;
      --learn: #8a4d17;
      --learn-soft: #fbeddc;
    }}
    body {{ margin: 0; font-family: Georgia, 'Times New Roman', serif; background: linear-gradient(180deg, #ede6d8 0%, var(--bg) 100%); color: var(--ink); }}
    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 32px 20px 60px; }}
    .topbar {{ display: grid; grid-template-columns: 320px minmax(0, 1.65fr) minmax(280px, 1fr); gap: 18px; align-items: flex-start; margin-bottom: 28px; }}
    .hero-copy {{ min-width:0; flex: 1 1 680px; max-width: 760px; grid-column: 1 / 3; }}
    h1 {{ font-size: 44px; margin: 0 0 8px; }}
    .subtitle {{ color: var(--muted); max-width: 760px; line-height: 1.5; }}
    .top-actions {{ display:flex; align-items:center; justify-content:center; gap:10px; margin-top: 48px; grid-column: 3; justify-self: center; }}
    .top-generate {{ padding: 16px 20px; font-size: 19px; line-height: 1; font-weight: 800; border-radius: 18px; box-shadow: 0 14px 30px rgba(23, 89, 74, 0.24); }}
    .top-generate[disabled] {{ background: #b8b0a6; cursor: not-allowed; opacity: 0.7; box-shadow:none; }}
    .shell {{ display: grid; grid-template-columns: 320px minmax(0, 1.65fr) minmax(280px, 1fr); gap: 18px; align-items: start; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 20px; box-shadow: 0 10px 30px rgba(40, 28, 16, 0.06); min-width: 0; overflow: hidden; }}
    .rail {{ position: sticky; top: 20px; max-height: calc(100vh - 40px); overflow: auto; }}
    .label {{ text-transform: uppercase; letter-spacing: 0.08em; font-size: 12px; color: var(--muted); margin-bottom: 8px; }}
    .section-label {{ font-size: 16px; font-weight: 700; color: var(--ink); margin-bottom: 14px; margin-top: 4px; }}
    .mono {{ font-family: Consolas, monospace; font-size: 13px; color: var(--muted); overflow-wrap: anywhere; word-break: break-word; }}
    .status {{ display: inline-block; padding: 6px 10px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-weight: 700; }}
    .status.error {{ background: #fbe7df; color: var(--warn); }}
    .progress-wrap {{ margin-top: 14px; }}
    .progress-meta {{ display: flex; justify-content: space-between; gap: 12px; font-size: 12px; color: var(--muted); margin-bottom: 8px; }}
    .progress-track {{ height: 10px; border-radius: 999px; background: #e8dfd3; overflow: hidden; border: 1px solid #d8cfc4; }}
    .progress-fill {{ height: 100%; background: linear-gradient(90deg, #17594a 0%, #2f8f77 100%); border-radius: 999px; transition: width 0.3s ease; }}
    .run-indicator {{ display: flex; align-items: center; gap: 10px; margin-top: 12px; color: var(--muted); font-size: 13px; }}
    .spinner {{ width: 18px; height: 18px; border: 2px solid #d8cfc4; border-top-color: var(--accent); border-radius: 999px; display: inline-block; animation: spin 0.8s linear infinite; opacity: 0; }}
    .spinner.is-running {{ opacity: 1; }}
    .generate-plan-button[disabled] {{ background: #b8b0a6; cursor: not-allowed; opacity: 0.7; }}
    .step-toggle {{ margin-top: 12px; display: inline-flex; align-items: center; gap: 8px; color: var(--muted); font-size: 12px; cursor: pointer; user-select: none; }}
    .step-toggle input {{ display: none; }}
    .step-toggle .caret {{ display: inline-block; width: 14px; height: 14px; position: relative; transition: transform 0.2s ease; }}
    .step-toggle input:checked ~ .caret {{ transform: rotate(90deg); }}
    .step-toggle .caret::before {{ content: '›'; position: absolute; font-size: 18px; font-weight: 700; color: var(--muted); line-height: 1; }}
    .step-history {{ margin-top: 10px; padding-left: 0; color: var(--muted); line-height: 1.6; }}
    .step-history li {{ margin-bottom: 4px; list-style: none; }}
    .step-history-wrap[hidden] {{ display: none; }}
    @keyframes spin {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}
    .plan-list {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }}
    .plan-item {{ display: flex; align-items: center; gap: 12px; border-radius: 14px; padding: 14px 16px; border: 1px solid var(--line); font-size: 19px; line-height: 1.4; transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease; }}
    .plan-item-clickable {{ padding: 0; overflow: hidden; }}
    .plan-link {{ display: flex; align-items: center; gap: 12px; width: 100%; padding: 14px 16px; color: inherit; text-decoration: none; }}
    .plan-link:hover, .plan-link:focus-visible {{ text-decoration: none; }}
    .plan-item-clickable:hover {{ transform: translateY(-2px) scale(1.012); box-shadow: 0 10px 22px rgba(29, 26, 22, 0.10); }}
    .plan-item-clickable:has(.plan-link:focus-visible) {{ transform: translateY(-2px) scale(1.012); box-shadow: 0 10px 22px rgba(29, 26, 22, 0.10); border-color: #b8cfc5; }}
    .leetcode-icon {{ margin-left: 6px; vertical-align: -1px; display: inline-block; opacity: 0.7; transition: transform 0.18s ease, opacity 0.18s ease; }}
    .plan-item-clickable:hover .leetcode-icon, .plan-item-clickable:has(.plan-link:focus-visible) .leetcode-icon {{ opacity: 1; transform: translate(1px, -1px); }}
    .task-badge {{ display: inline-block; min-width: 72px; text-align: center; padding: 6px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }}
    .task-redo {{ background: var(--review-soft); border-color: #c8dff0; }}
    .task-redo .task-badge {{ background: var(--review); color: white; }}
    .task-learn {{ background: var(--learn-soft); border-color: #ecd3b6; }}
    .task-learn .task-badge {{ background: var(--learn); color: white; }}
    .task-generic {{ background: #f7f2ea; }}
    .task-generic .task-badge {{ background: #756a5f; color: white; }}
    .task-text {{ font-weight: 700; }}
    .why {{ color: var(--muted); line-height: 1.7; overflow-wrap: anywhere; word-break: break-word; }}
    .why-paragraph {{ margin: 0 0 12px; }}
    .why-paragraph:last-child {{ margin-bottom: 0; }}
    .problem-reasons {{ margin: 0; padding-left: 0; color: var(--muted); line-height: 1.8; display: grid; gap: 10px; }}
    .problem-reason-item {{ }}
    .problem-number {{ font-weight: 700; }}
    .problem-number-review {{ color: var(--review); }}
    .problem-number-learn {{ color: var(--learn); }}
    .problem-number-task {{ color: var(--ink); }}
    .problem-reason-badge {{ display: inline-block; padding: 3px 6px; border-radius: 4px; font-size: 9px; font-weight: 700; letter-spacing: 0.03em; text-transform: uppercase; margin-right: 6px; }}
    .problem-reason-review {{ background: var(--review); color: white; }}
    .problem-reason-learn {{ background: var(--learn); color: white; }}
    .problem-reason-task {{ background: #756a5f; color: white; }}
    .problem-reasons-empty {{ color: var(--muted); }}
    form {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
    button {{ background: var(--accent); color: white; border: 0; border-radius: 999px; padding: 10px 16px; font-weight: 700; cursor: pointer; }}
    .generate-plan-button {{ padding: 12px 20px; font-size: 14px; font-weight: 700; border-radius: 999px; white-space: nowrap; }}
    .agent-header {{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:10px; }}
    .inline-label {{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }}
    .inline-label .label, .inline-label .section-label {{ margin:0; }}
    .help-wrap {{ position: relative; display: inline-flex; align-items: center; }}
    .help-button {{ display:inline-flex; align-items:center; justify-content:center; width:20px; height:20px; border-radius:999px; border:1px solid var(--line); background:#faf6ef; color:var(--muted); font-weight:700; font-size:11px; cursor:help; text-decoration:none; padding:0; }}
    .help-tooltip {{ position: fixed; width: min(320px, calc(100vw - 32px)); padding: 10px 12px; background:#fffdf8; border:1px solid var(--line); border-radius:12px; box-shadow:0 12px 30px rgba(40, 28, 16, 0.14); color:var(--muted); line-height:1.45; font-size:12px; z-index:9999; opacity:0; visibility:hidden; transform:translateY(-4px); transition:opacity 0.14s ease, transform 0.14s ease, visibility 0.14s ease; pointer-events:none; }}
    .help-tooltip.is-visible {{ opacity:1; visibility:visible; }}
    .help-tooltip.is-above {{ transform:translateY(-6px); }}
    .help-tooltip.is-below {{ transform:translateY(6px); }}
    .help-tooltip::before {{ content:""; position:absolute; right:14px; width:12px; height:12px; background:#fffdf8; transform:rotate(45deg); }}
    .help-tooltip.is-below::before {{ top:-7px; border-left:1px solid var(--line); border-top:1px solid var(--line); }}
    .help-tooltip.is-above::before {{ bottom:-7px; border-right:1px solid var(--line); border-bottom:1px solid var(--line); }}
    .agent-actions {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:16px; }}
    .agent-actions form {{ margin:0; }}
    .status-row {{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin: 10px 0 0; flex-wrap:wrap; }}
    .control-row {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }}
    .control-actions {{ display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; min-width: 0; }}
    .control-actions form {{ margin: 0; }}
    input[type=time], select {{ border: 1px solid var(--line); border-radius: 999px; padding: 10px 14px; background: white; }}
    .meta {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .timeline {{ position: relative; display: grid; gap: 10px; }}
    .timeline::before {{ content: ''; position: absolute; left: 11px; top: 6px; bottom: 6px; width: 2px; background: linear-gradient(180deg, #d8cfc4 0%, #e8dfd3 100%); }}
    .timeline-item {{ position: relative; display: flex; gap: 12px; align-items: center; padding: 12px 14px 12px 0; text-decoration: none; color: inherit; border-radius: 14px; }}
    .timeline-item:hover {{ background: #faf6ef; }}
    .timeline-item.is-selected {{ background: #f2f8f5; }}
    .timeline-dot {{ position: relative; z-index: 1; width: 10px; height: 10px; margin-left: 7px; border-radius: 999px; background: #b7ada1; border: 4px solid var(--panel); box-shadow: 0 0 0 1px #cfc4b7; flex: 0 0 auto; }}
    .timeline-item.is-selected .timeline-dot {{ background: var(--accent); box-shadow: 0 0 0 1px #8eb7ab; }}
    .timeline-copy {{ display: grid; min-width: 0; }}
    .timeline-date {{ font-weight: 700; color: var(--ink); white-space: pre-line; }}
    .timeline-id {{ font-size: 12px; }}
    .timeline-tag {{ margin-left: auto; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--accent); background: var(--accent-soft); border-radius: 999px; padding: 6px 10px; font-weight: 700; }}
    .timeline-empty {{ color: var(--muted); }}
    .meta div {{ padding: 12px 14px; background: #faf6ef; border-radius: 14px; border: 1px solid var(--line); min-width: 0; overflow-wrap: anywhere; word-break: break-word; }}
    @media (max-width: 980px) {{ .shell {{ grid-template-columns: 1fr; }} .rail {{ position: static; max-height: none; overflow: visible; }} .topbar {{ align-items: flex-start; gap: 16px; }} .top-actions {{ width: 100%; justify-content: center; margin-top: 0; }} .top-generate {{ width: 100%; justify-content: center; padding: 18px 22px; font-size: 17px; border-radius: 16px; }} h1 {{ font-size: 34px; }} .plan-item {{ font-size: 17px; align-items: flex-start; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="hero-copy">
        <h1>LeetLoop</h1>
        <div class="subtitle">A local daily interview-practice app that keeps your LeetCode plan visible, stateful, and scheduled without relying on a hidden OS task.</div>
      </div>
      <div class="top-actions">
        <form id="run-now-form" method="post" action="/run-now" style="margin: 0; display: inline-flex; width: auto;">
          <button class="generate-plan-button top-generate" type="submit" style="display:inline-flex; align-items:center; justify-content:center; width:auto; padding: 13px 18px; font-size: 19px; min-height: 0; border-radius: 16px;" {'disabled' if snapshot.get('is_running') else ''}>Generate Plan</button>
        </form>
      </div>
    </div>
    <div class="shell">
      <aside class="card rail">
        <div class="inline-label"><div class="label">History Timeline</div><div class="help-wrap"><button type="button" class="help-button" aria-label="Explain history timeline">?</button><div class="help-tooltip" role="tooltip">Browse prior generated plans. Clicking a run loads that day's saved recommendation and reasoning without changing your current config.</div></div></div>
        {history_timeline}
      </aside>
      <section class="card">
        <div class="label">Today's Plan</div>
        <div class="mono">Run ID: {html.escape(run_id)}</div>
        <div style="height: 12px"></div>
        {plan_html}
        <div style="height: 18px"></div>
        <div class="inline-label"><div class="label">Why now</div><div class="help-wrap"><button type="button" class="help-button" aria-label="Explain why now">?</button><div class="help-tooltip" role="tooltip">A short user-facing summary of why this set of questions is high leverage today, based on staleness, weak mastery, and important missing patterns.</div></div></div>
        <div class="why">{why_html}</div>
        <div style="height: 14px"></div>
        <div class="inline-label"><div class="label">Problem by problem</div><div class="help-wrap"><button type="button" class="help-button" aria-label="Explain problem by problem">?</button><div class="help-tooltip" role="tooltip">One plain-English reason for each selected problem so you can quickly see what weakness or coverage gap it targets.</div></div></div>
        <div class="why">{problem_reasons_html}</div>
      </section>
      <aside class="card">
        <div class="agent-header">
          <div class="section-label" style="margin: 0;">Agent</div>
          <div class="help-wrap">
            <button type="button" class="help-button" aria-label="Explain agent controls">?</button>
            <div class="help-tooltip" role="tooltip">
              <div><strong>Restart Agent</strong> reloads the background LeetLoop service without changing your saved config.</div>
              <div style="height:8px"></div>
              <div><strong>Stop Agent</strong> shuts the background service down completely. Scheduling stops until you start LeetLoop again with <span class="mono">run_app.bat</span>.</div>
            </div>
          </div>
        </div>
        <div class="agent-actions">
          <form method="post" action="/agent-control">
            <button type="submit" name="action" value="restart" style="background: #8b6f47;">Restart Agent</button>
          </form>
          <form method="post" action="/agent-control">
            <button type="submit" name="action" value="stop" style="background: #b4433c;">Stop Agent</button>
          </form>
        </div>
        <div class="control-row">
          <div class="section-label" style="margin: 0;">Service Status</div>
        </div>
        <div class="status-row">
          <div class="status {'error' if snapshot['last_status'] == 'error' else ''}">{html.escape(snapshot['last_status'])}</div>
        </div>
        <div class="progress-wrap">
          <div class="progress-meta">
            <span>{html.escape(snapshot.get('progress_label') if snapshot.get('progress_label') else ('Step ' + str(snapshot.get('progress_step_index') or 0) + '/' + str(snapshot.get('progress_step_total') or 0)) if snapshot.get('is_running') else '')}</span>
            <span>{'%' + str(int(snapshot.get('progress_percent') or 0)) if snapshot.get('is_running') else ''}</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" style="width: {int(snapshot.get('progress_percent') or 0)}%"></div>
          </div>
          <div class="run-indicator">
            <span class="spinner {'is-running' if snapshot.get('is_running') else ''}"></span>
            <span>{'Planner is running...' if snapshot.get('is_running') else ''}</span>
          </div>
          <label class="step-toggle">
            <input id="show-step-history" type="checkbox">
            <span class="caret"></span>
            <span>Show previous steps</span>
          </label>
          <div id="step-history-wrap" class="step-history-wrap" hidden>
            <ul class="step-history">{progress_history_items or '<li>No steps recorded yet.</li>'}</ul>
          </div>
        </div>
        <div style="height: 6px"></div>
        <div class="why" style="background:#faf6ef; border:1px solid var(--line); border-radius:12px; padding:12px;">{html.escape(snapshot['last_message'] or 'Ready.')}</div>
        {f'<label class="step-toggle"><input id="show-run-details" type="checkbox"><span class="caret"></span><span>Show run details</span></label><div id="run-details-wrap" class="step-history-wrap" hidden><div style="height: 8px"></div><pre class="mono" style="white-space: pre-wrap; background: #faf6ef; border: 1px solid var(--line); border-radius: 12px; padding: 12px; max-height: 200px; overflow: auto;">{html.escape(snapshot.get("last_detail") or "")}</pre></div>' if snapshot.get('last_detail') else ''}
        <div style="height: 16px"></div>
        <div class="section-label">Configuration</div>
        <div class="inline-label"><div class="label">Planning mode</div><div class="help-wrap"><button type="button" class="help-button" aria-label="Explain planning mode">?</button><div class="help-tooltip" role="tooltip">Changes the target mix of review vs gap-fill problems. This updates planner config and affects the next run, not the already displayed plan.</div></div></div>
        <form method="post" action="/planning-bias">
          <select name="planning_bias" required>
            {mode_options}
          </select>
          <button type="submit">Apply</button>
        </form>
        <div style="height: 12px"></div>
        <div class="inline-label"><div class="label">Timezone</div><div class="help-wrap"><button type="button" class="help-button" aria-label="Explain timezone">?</button><div class="help-tooltip" role="tooltip">Controls how run times are displayed and how the daily schedule is interpreted. New runs will also use this timezone when saved.</div></div></div>
        <form method="post" action="/timezone">
          <select name="timezone" required>
            {timezone_options}
          </select>
          <button type="submit">Save</button>
        </form>
        <div style="height: 12px"></div>
        <div class="inline-label"><div class="label">Daily schedule</div><div class="help-wrap"><button type="button" class="help-button" aria-label="Explain daily schedule">?</button><div class="help-tooltip" role="tooltip">App will run at this time each day (checks every 20s while running)
</div></div></div>
        <form method="post" action="/schedule" style="display: flex; gap: 8px; align-items: center;">
          <input type="time" name="daily_time" value="{html.escape(config['daily_time'])}">
          <button type="submit" name="action" value="update-schedule">Set</button>
          <button type="submit" name="action" value="disable-schedule" style="background: #999;">Clear</button>
        </form>
        <div style="height: 12px"></div>
        <div class="inline-label"><div class="label">Launch At Login</div><div class="help-wrap"><button type="button" class="help-button" aria-label="Explain launch at login">?</button><div class="help-tooltip" role="tooltip">Tells your system to start the LeetLoop background agent after login so scheduled runs can happen without manually opening the app first.</div></div></div>
        <form method="post" action="/launch-at-login" style="display: flex; gap: 8px; align-items: center;">
          <button type="submit" name="action" value="enable" style="background: {'#2d8a56' if autostart_label == 'Enabled' else '#999'};">Enable</button>
          <button type="submit" name="action" value="disable" style="background: {'#b4433c' if autostart_label == 'Disabled' else '#999'};">Disable</button>
        </form>
        <div style="height: 18px"></div>
        <div class="section-label">Status</div>
        <div class="meta">
          <div><strong>Next run</strong><br><span class="mono">{html.escape(next_run)}</span></div>
          <div><strong>Last finished</strong><br><span class="mono">{html.escape(format_saved_iso(snapshot['last_finished_at']))}</span></div>
          <div><strong>Focus mode</strong><br><span class="mono">{html.escape(str(focus_mode))}</span></div>
          <div><strong>Confidence</strong><br><span class="mono">{html.escape(str(confidence))}</span></div>
          <div><strong>Planning bias</strong><br><span class="mono">{html.escape(planner_bias)}</span></div>
          <div><strong>Timezone</strong><br><span class="mono">{html.escape(timezone_name)}</span></div>
          <div><strong>Target shape</strong><br><span class="mono">{html.escape(str(target_shape or 'Unknown'))}</span></div>
          <div><strong>Selected run</strong><br><span class="mono">{html.escape(selected_run_name or 'None')}</span></div>
          <div><strong>Latest run</strong><br><span class="mono">{html.escape(snapshot['last_run_dir'] or (latest_run_dir().name if latest_run_dir() else 'None'))}</span></div>
        </div>
      </aside>
    </div>
  </div>
  <script>
    const isRunning = {str(snapshot.get("is_running", False)).lower()};
    const currentSelectedRun = {json.dumps(selected_run_name)};
    const latestRunName = {json.dumps(snapshot['last_run_dir'] or (latest_run_dir().name if latest_run_dir() else None))};
    const historyToggle = document.getElementById('show-step-history');
    const historyWrap = document.getElementById('step-history-wrap');
    const detailsToggle = document.getElementById('show-run-details');
    const detailsWrap = document.getElementById('run-details-wrap');
    const HISTORY_STORAGE_KEY = 'leetloop-show-step-history';
    const DETAILS_STORAGE_KEY = 'leetloop-show-run-details';
    const FOLLOW_LATEST_AFTER_RUN_KEY = 'leetloop-follow-latest-after-run';
    
    if (historyToggle && historyWrap) {{
      // Restore state from localStorage
      const savedState = localStorage.getItem(HISTORY_STORAGE_KEY) === 'true';
      historyToggle.checked = savedState;
      historyWrap.hidden = !savedState;
      
      // Save state on change
      historyToggle.addEventListener('change', () => {{
        const isChecked = historyToggle.checked;
        localStorage.setItem(HISTORY_STORAGE_KEY, isChecked);
        historyWrap.hidden = !isChecked;
      }});
    }}
    
    if (detailsToggle && detailsWrap) {{
      // Restore state from localStorage
      const savedState = localStorage.getItem(DETAILS_STORAGE_KEY) === 'true';
      detailsToggle.checked = savedState;
      detailsWrap.hidden = !savedState;
      
      // Save state on change
      detailsToggle.addEventListener('change', () => {{
        const isChecked = detailsToggle.checked;
        localStorage.setItem(DETAILS_STORAGE_KEY, isChecked);
        detailsWrap.hidden = !isChecked;
      }});
    }}
    
    const helpPairs = Array.from(document.querySelectorAll('.help-wrap')).map((wrap) => {{
      return {{ wrap, button: wrap.querySelector('.help-button'), tooltip: wrap.querySelector('.help-tooltip') }};
    }}).filter((item) => item.button && item.tooltip);
    const positionTooltip = (button, tooltip) => {{
      const rect = button.getBoundingClientRect();
      const tooltipWidth = Math.min(320, window.innerWidth - 32);
      const tooltipHeight = Math.max(72, tooltip.offsetHeight || 96);
      const showAbove = rect.top > tooltipHeight + 24;
      const top = showAbove ? (rect.top - tooltipHeight - 14) : (rect.bottom + 14);
      const left = Math.max(16, Math.min(rect.right - tooltipWidth, window.innerWidth - tooltipWidth - 16));
      tooltip.style.width = tooltipWidth + 'px';
      tooltip.style.left = left + 'px';
      tooltip.style.top = top + 'px';
      tooltip.classList.toggle('is-above', showAbove);
      tooltip.classList.toggle('is-below', !showAbove);
    }};
    helpPairs.forEach((item) => {{
      const showTooltip = () => {{
        positionTooltip(item.button, item.tooltip);
        item.tooltip.classList.add('is-visible');
      }};
      const hideTooltip = () => item.tooltip.classList.remove('is-visible');
      item.wrap.addEventListener('mouseenter', showTooltip);
      item.wrap.addEventListener('mouseleave', hideTooltip);
      item.wrap.addEventListener('focusin', showTooltip);
      item.wrap.addEventListener('focusout', hideTooltip);
    }});
    window.addEventListener('resize', () => {{
      helpPairs.forEach((item) => {{
        if (item.tooltip.classList.contains('is-visible')) positionTooltip(item.button, item.tooltip);
      }});
    }});
    window.addEventListener('scroll', () => {{
      helpPairs.forEach((item) => {{
        if (item.tooltip.classList.contains('is-visible')) positionTooltip(item.button, item.tooltip);
      }});
    }}, true);

    const runNowForm = document.getElementById('run-now-form');
    if (runNowForm) {{
      runNowForm.addEventListener('submit', () => {{
        sessionStorage.setItem(FOLLOW_LATEST_AFTER_RUN_KEY, 'true');
        const button = runNowForm.querySelector('button[type="submit"]');
        if (button) {{
          button.disabled = true;
          button.textContent = 'Running...';
        }}
      }});
    }}

    const shouldFollowLatest = sessionStorage.getItem(FOLLOW_LATEST_AFTER_RUN_KEY) === 'true';
    if (!isRunning && shouldFollowLatest && latestRunName) {{
      sessionStorage.removeItem(FOLLOW_LATEST_AFTER_RUN_KEY);
      if (currentSelectedRun !== latestRunName) {{
        const url = new URL(window.location.href);
        url.searchParams.set('run', latestRunName);
        window.location.replace(url.toString());
      }}
    }}

    const shouldPauseRefresh = () => {{
      const active = document.activeElement;
      if (active && active !== document.body) {{
        const tag = (active.tagName || '').toLowerCase();
        if (['input', 'select', 'textarea', 'button', 'option'].includes(tag) || active.isContentEditable) {{
          return true;
        }}
      }}
      const selection = window.getSelection ? window.getSelection() : null;
      if (selection && String(selection).trim()) {{
        return true;
      }}
      return false;
    }};

    const autoRefresh = () => {{
      if (shouldPauseRefresh()) {{
        window.setTimeout(autoRefresh, 2000);
        return;
      }}
      window.location.reload();
    }};

    if (isRunning) {{
      window.setTimeout(autoRefresh, 1500);
    }} else {{
      // Even when idle, periodically check for scheduled runs starting
      window.setTimeout(autoRefresh, 3000);
    }}
  </script>
</body>
</html>
"""


class LeetLoopHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            body = b"ok"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        query = parse_qs(parsed.query)
        selected_run_name = (query.get("run") or [None])[0]
        body = build_page(selected_run_name=selected_run_name).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        form = parse_qs(raw)

        if self.path == "/run-now":
            trigger_run("manual")
            return self.redirect_home()

        if self.path == "/agent-control":
            action = (form.get("action") or [""])[0]
            if action == "restart":
                with state_lock:
                    service_state["last_status"] = "ok"
                    service_state["last_message"] = "Agent restarting..."
                body = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="2;url=/"><title>LeetLoop Restarting</title>
<style>body{font-family:Georgia,serif;background:#f6f1e8;color:#2e241c;display:grid;place-items:center;min-height:100vh;margin:0} .card{background:#fffdf9;border:1px solid #e4d9ca;border-radius:18px;padding:28px;max-width:520px;box-shadow:0 12px 40px rgba(38,24,16,.08)} h1{margin:0 0 10px;font-size:28px} p{margin:0 0 10px;line-height:1.6;color:#5f5146}</style></head>
<body><div class="card"><h1>Restarting LeetLoop</h1><p>The background agent is restarting now.</p><p>This page will try to return to the app automatically.</p></div></body></html>"""
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body.encode("utf-8"))))
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))
                self.wfile.flush()
                request_server_shutdown(restart=True)
                return
            if action == "stop":
                with state_lock:
                    service_state["last_status"] = "ok"
                    service_state["last_message"] = "Agent stopping..."
                body = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>LeetLoop Stopped</title>
<style>body{font-family:Georgia,serif;background:#f6f1e8;color:#2e241c;display:grid;place-items:center;min-height:100vh;margin:0} .card{background:#fffdf9;border:1px solid #e4d9ca;border-radius:18px;padding:28px;max-width:560px;box-shadow:0 12px 40px rgba(38,24,16,.08)} h1{margin:0 0 10px;font-size:28px} p{margin:0 0 10px;line-height:1.6;color:#5f5146} code{background:#f3ece1;padding:2px 6px;border-radius:6px}</style></head>
<body><div class="card"><h1>LeetLoop Agent Stopped</h1><p>The background agent has been asked to shut down.</p><p>To start it again, run <code>run_app.bat</code>.</p></div></body></html>"""
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body.encode("utf-8"))))
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))
                self.wfile.flush()
                request_server_shutdown(restart=False)
                return
            with state_lock:
                service_state["last_status"] = "error"
                service_state["last_message"] = "Unknown agent control action."
            return self.redirect_home()

        if self.path == "/planning-bias":
            planning_bias = (form.get("planning_bias") or [""])[0]
            if planning_bias in PLANNING_MODE_OPTIONS:
                planner_config = load_planner_config()
                planner_config["planning_bias"] = planning_bias
                save_planner_config(planner_config)
                with state_lock:
                    service_state["last_message"] = f"Planning mode updated to {planning_bias}."
                    service_state["last_status"] = "ok"
            else:
                with state_lock:
                    service_state["last_message"] = "Invalid planning mode."
                    service_state["last_status"] = "error"
            return self.redirect_home()

        if self.path == "/timezone":
            timezone_name = (form.get("timezone") or [""])[0]
            planner_config = load_planner_config()
            planner_config["timezone"] = timezone_name
            save_planner_config(planner_config)
            resolved = current_timezone_name()
            with state_lock:
                if resolved == timezone_name:
                    service_state["last_message"] = f"Timezone updated to {timezone_name}."
                    service_state["last_status"] = "ok"
                else:
                    service_state["last_message"] = f"Timezone data for {timezone_name} is unavailable on this machine. Falling back to {resolved}. Install tzdata and rerun setup to enable full timezone support."
                    service_state["last_status"] = "error"
            return self.redirect_home()

        if self.path == "/launch-at-login":
            action = (form.get("action") or [""])[0]
            message = install_autostart() if action == "enable" else uninstall_autostart()
            with state_lock:
                service_state["last_message"] = message
                service_state["last_status"] = "ok"
            return self.redirect_home()

        if self.path == "/schedule":
            action = (form.get("action") or [""])[0]
            if action == "disable-schedule":
                config = load_app_config()
                config["daily_time"] = ""
                save_app_config(config)
                with state_lock:
                    service_state["last_message"] = "Daily schedule disabled."
                    service_state["last_status"] = "ok"
            else:
                daily_time = (form.get("daily_time") or [""])[0]
                if daily_time and validate_daily_time(daily_time):
                    config = load_app_config()
                    config["daily_time"] = daily_time
                    save_app_config(config)
                    with state_lock:
                        service_state["last_message"] = f"Daily run time updated to {daily_time}."
                        service_state["last_status"] = "ok"
                else:
                    with state_lock:
                        service_state["last_message"] = "Invalid daily time. Use HH:MM."
                        service_state["last_status"] = "error"
            return self.redirect_home()

        self.send_error(HTTPStatus.NOT_FOUND)

    def redirect_home(self):
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, format, *args):
        return


def request_server_shutdown(restart: bool = False) -> bool:
    server = ACTIVE_SERVER
    if server is None:
        return False

    def _shutdown():
        try:
            server.shutdown()
            server.server_close()
        finally:
            if restart:
                time.sleep(0.5)
                spawn_background_agent()

    threading.Thread(target=_shutdown, daemon=False).start()
    return True


def scheduler_loop():
    print("[SCHEDULER] Scheduler thread started", flush=True)
    check_count = 0
    while True:
        try:
            config = load_app_config()
            daily_time = str(config.get("daily_time", "") or "").strip()
            
            check_count += 1
            if check_count % 6 == 1:  # Log every 60 seconds
                print(f"[SCHEDULER] Check #{check_count}: daily_time='{daily_time}'", flush=True)

            if daily_time:
                now = datetime.datetime.now(datetime.UTC).astimezone(current_timezone())
                today = now.date().isoformat()
                tz_name = current_timezone_name()

                try:
                    sched_hour, sched_min = map(int, daily_time.split(":"))
                    with state_lock:
                        already_ran = service_state.get("last_scheduled_date") == today
                        currently_running = service_state.get("is_running", False)

                    is_time_match = (now.hour == sched_hour and now.minute == sched_min)
                    
                    if check_count % 6 == 1:  # Log every 60 seconds
                        print(f"[SCHEDULER] NOW: {now.strftime('%H:%M')} | SCHED: {daily_time} | TZ: {tz_name} | MATCH: {is_time_match} | ALREADY_RAN: {already_ran} | RUNNING: {currently_running}", flush=True)

                    if is_time_match and not already_ran and not currently_running:
                        print(f"[SCHEDULER] *** TRIGGERING RUN at {now.strftime('%H:%M')} (scheduled: {daily_time}) ***", flush=True)
                        with state_lock:
                            service_state["last_scheduled_date"] = today
                            service_state["last_message"] = f"Scheduled run triggered for {daily_time}."
                        trigger_run("schedule")
                except (ValueError, IndexError) as e:
                    print(f"[SCHEDULER] Parse error: {e}", flush=True)
                    with state_lock:
                        service_state["last_status"] = "error"
                        service_state["last_message"] = "Invalid daily schedule time in app config. Use HH:MM."
        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}", flush=True)
            with state_lock:
                service_state["last_status"] = "error"
                service_state["last_message"] = f"Scheduler error: {e}"

        time.sleep(10)


def initialize_state_from_history():
    with state_lock:
        service_state["last_run_date"] = infer_last_run_date_from_history()
        service_state.setdefault("last_scheduled_date", None)


def run_server(background: bool = False):
    global ACTIVE_SERVER

    config = load_app_config()
    initialize_state_from_history()

    scheduler = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler.start()

    host = config["host"]
    port = int(config["port"])
    server = ThreadingHTTPServer((host, port), LeetLoopHandler)
    ACTIVE_SERVER = server
    write_agent_pid()
    url = server_url(config)

    print(f"LeetLoop agent running at {url}")
    print(f"Daily run time: {config['daily_time']} {current_timezone_name()}")

    if not background and config.get("open_browser_on_start", True):
        webbrowser.open(url)

    try:
        server.serve_forever()
    finally:
        ACTIVE_SERVER = None
        clear_agent_pid()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--ui", action="store_true")
    parser.add_argument("--check-setup", action="store_true")
    parser.add_argument("--install-launch-at-login", action="store_true")
    parser.add_argument("--uninstall-launch-at-login", action="store_true")
    args = parser.parse_args()

    if args.check_setup:
        raise SystemExit(run_setup_check())

    if args.install_launch_at_login:
        print(install_autostart())
        return
    if args.uninstall_launch_at_login:
        print(uninstall_autostart())
        return

    cfg = load_app_config()

    if args.ui:
        validate_startup_environment()
        if not server_is_running(cfg):
            if port_is_open(cfg):
                stop_recorded_agent()
                deadline = time.time() + 3
                while time.time() < deadline and port_is_open(cfg):
                    time.sleep(0.2)
                if port_is_open(cfg):
                    stop_processes_on_port(cfg)
                    deadline = time.time() + 5
                    while time.time() < deadline and port_is_open(cfg):
                        time.sleep(0.2)
            if not port_is_open(cfg):
                spawn_background_agent()
            if not wait_for_server():
                raise RuntimeError("Background agent did not start successfully.")
        if cfg.get("open_browser_on_start", True):
            webbrowser.open(server_url(cfg))
        return

    if server_is_running(cfg):
        if not args.background and cfg.get("open_browser_on_start", True):
            webbrowser.open(server_url(cfg))
        return

    validate_startup_environment()

    run_server(background=args.background)


if __name__ == "__main__":
    main()
