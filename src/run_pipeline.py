from dotenv import load_dotenv

import json
import os
import re
import datetime
import webbrowser
import requests
import time
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

if sys.version_info < (3, 10):
    print("LeetLoop requires Python 3.10 or newer.")
    raise SystemExit(1)

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from startup_checks import missing_credentials_message, missing_env_file_message

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=ENV_PATH)

HISTORY_DIR = os.path.join(PROJECT_ROOT, "history")
os.makedirs(HISTORY_DIR, exist_ok=True)

GRAPHQL_URL = "https://leetcode.com/graphql"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_TIMEZONE = "America/Los_Angeles"

COOLDOWN_HOURS = 24
FRAGILE_MIN_HOURS = 24
FRAGILE_MAX_DAYS = 7

DEFAULT_GAP_FILL_CANDIDATES = [
    {"title": "Minimum Window Substring", "slug": "minimum-window-substring", "difficulty": "Hard", "reason": "elite sliding-window flagship"},
    {"title": "Daily Temperatures", "slug": "daily-temperatures", "difficulty": "Medium", "reason": "canonical monotonic-stack problem"},
    {"title": "Serialize and Deserialize Binary Tree", "slug": "serialize-and-deserialize-binary-tree", "difficulty": "Hard", "reason": "major tree/design interview pattern"},
    {"title": "Largest Rectangle in Histogram", "slug": "largest-rectangle-in-histogram", "difficulty": "Hard", "reason": "canonical hard monotonic-stack problem"},
    {"title": "Edit Distance", "slug": "edit-distance", "difficulty": "Hard", "reason": "major DP pattern"},
    {"title": "Task Scheduler", "slug": "task-scheduler", "difficulty": "Medium", "reason": "common counting/greedy scheduling pattern"},
    {"title": "Kth Largest Element in an Array", "slug": "kth-largest-element-in-an-array", "difficulty": "Medium", "reason": "common heap/select pattern"},
    {"title": "Word Ladder", "slug": "word-ladder", "difficulty": "Hard", "reason": "classic BFS shortest-path pattern"},
    {"title": "Binary Tree Maximum Path Sum", "slug": "binary-tree-maximum-path-sum", "difficulty": "Hard", "reason": "high-value tree DP interview anchor"},
    {"title": "Find Median from Data Stream", "slug": "find-median-from-data-stream", "difficulty": "Hard", "reason": "canonical two-heaps design problem"},
    {"title": "Longest Increasing Subsequence", "slug": "longest-increasing-subsequence", "difficulty": "Medium", "reason": "core DP and binary-search pattern"},
    {"title": "Number of Islands", "slug": "number-of-islands", "difficulty": "Medium", "reason": "canonical graph traversal interview anchor"},
    {"title": "Course Schedule", "slug": "course-schedule", "difficulty": "Medium", "reason": "core graph cycle-detection interview anchor"},
    {"title": "Top K Frequent Elements", "slug": "top-k-frequent-elements", "difficulty": "Medium", "reason": "common bucket/heap frequency pattern"},
    {"title": "Product of Array Except Self", "slug": "product-of-array-except-self", "difficulty": "Medium", "reason": "canonical prefix/suffix array pattern"},
    {"title": "Longest Consecutive Sequence", "slug": "longest-consecutive-sequence", "difficulty": "Medium", "reason": "high-value hash-set interview anchor"},
    {"title": "Group Anagrams", "slug": "group-anagrams", "difficulty": "Medium", "reason": "canonical hashing and grouping pattern"},
    {"title": "Find Minimum in Rotated Sorted Array", "slug": "find-minimum-in-rotated-sorted-array", "difficulty": "Medium", "reason": "core rotated-array binary-search anchor"},
    {"title": "Merge Intervals", "slug": "merge-intervals", "difficulty": "Medium", "reason": "classic interval consolidation pattern"},
    {"title": "Coin Change", "slug": "coin-change", "difficulty": "Medium", "reason": "major bottom-up DP interview anchor"},
    {"title": "Validate Binary Search Tree", "slug": "validate-binary-search-tree", "difficulty": "Medium", "reason": "high-frequency tree invariant question"},
    {"title": "Sliding Window Maximum", "slug": "sliding-window-maximum", "difficulty": "Hard", "reason": "important deque/sliding-window flagship"},
    {"title": "Trapping Rain Water", "slug": "trapping-rain-water", "difficulty": "Hard", "reason": "elite two-pointer / stack interview anchor"},
]

INTERVIEW_CORE_PRIORITY_BONUS = {
    "minimum-window-substring": 5.5,
    "daily-temperatures": 5.0,
    "serialize-and-deserialize-binary-tree": 4.6,
    "largest-rectangle-in-histogram": 4.6,
    "edit-distance": 4.2,
    "task-scheduler": 4.0,
    "kth-largest-element-in-an-array": 4.0,
    "word-ladder": 4.2,
    "binary-tree-maximum-path-sum": 4.1,
    "find-median-from-data-stream": 4.0,
    "longest-increasing-subsequence": 4.7,
    "number-of-islands": 4.8,
    "course-schedule": 4.8,
    "top-k-frequent-elements": 4.0,
    "product-of-array-except-self": 4.0,
    "longest-consecutive-sequence": 4.8,
    "group-anagrams": 4.2,
    "search-in-rotated-sorted-array": 4.2,
    "find-minimum-in-rotated-sorted-array": 4.3,
    "merge-intervals": 4.2,
    "coin-change": 4.9,
    "binary-tree-level-order-traversal": 3.8,
    "validate-binary-search-tree": 4.3,
    "lowest-common-ancestor-of-a-binary-tree": 4.0,
    "rotting-oranges": 3.8,
    "subarray-sum-equals-k": 4.0,
    "sliding-window-maximum": 4.1,
    "find-all-anagrams-in-a-string": 3.8,
    "trapping-rain-water": 4.0,
    "best-time-to-buy-and-sell-stock": 3.5,
}

CANONICAL_REVIEW_BONUS = {
    "lru-cache": 5.0,
    "median-of-two-sorted-arrays": 5.0,
    "merge-k-sorted-lists": 4.5,
    "word-break": 4.0,
    "course-schedule-ii": 4.0,
    "jump-game": 3.5,
    "unique-paths": 3.0,
    "container-with-most-water": 3.0,
    "implement-trie-prefix-tree": 3.5,
    "basic-calculator-ii": 3.0,
}

DEFAULT_REVIEW_PRIORITY_BONUS = {
    "median-of-two-sorted-arrays": 6.0,
    "lru-cache": 5.5,
    "merge-k-sorted-lists": 5.0,
    "word-break": 4.5,
    "course-schedule-ii": 4.5,
    "implement-trie-prefix-tree": 4.0,
    "jump-game": 3.5,
    "container-with-most-water": 3.5,
    "basic-calculator-ii": 3.5,
    "unique-paths": 3.0,
}

DEFAULT_REVIEW_DEPRIORITIZED_SLUGS = {
    "find-elements-in-a-contaminated-binary-tree",
    "equal-sum-grid-partition-i",
    "count-subarrays-of-length-three-with-a-condition",
    "a-number-after-a-double-reversal",
    "score-of-a-string",
    "counting-words-with-a-given-prefix",
}

LOW_TRANSFER_EASY_SLUGS = {
    "fizz-buzz",
    "find-pivot-index",
    "palindrome-number",
    "roman-to-integer",
    "longest-common-prefix",
    "valid-palindrome",
    "remove-duplicates-from-sorted-array",
    "remove-element",
}

OBSCURE_CONTEST_KEYWORDS = (
    "stone-game",
    "strange-",
    "minimum-number-of",
    "maximum-number-of",
    "grid-game",
)

# Comprehensive internal mapping of LeetCode problems
# Maps normalized problem title (lowercase) to (frontend_id, slug)
PROBLEM_LOOKUP = {
    "two sum": (1, "two-sum"),
    "add two numbers": (2, "add-two-numbers"),
    "longest substring without repeating characters": (3, "longest-substring-without-repeating-characters"),
    "median of two sorted arrays": (4, "median-of-two-sorted-arrays"),
    "longest palindromic substring": (5, "longest-palindromic-substring"),
    "zigzag conversion": (6, "zigzag-conversion"),
    "reverse integer": (7, "reverse-integer"),
    "string to integer (atoi)": (8, "string-to-integer-atoi"),
    "palindrome number": (9, "palindrome-number"),
    "regular expression matching": (10, "regular-expression-matching"),
    "container with most water": (11, "container-with-most-water"),
    "integer to roman": (12, "integer-to-roman"),
    "roman to integer": (13, "roman-to-integer"),
    "longest common prefix": (14, "longest-common-prefix"),
    "3sum": (15, "3sum"),
    "3sum closest": (16, "3sum-closest"),
    "letter combinations of a phone number": (17, "letter-combinations-of-a-phone-number"),
    "4sum": (18, "4sum"),
    "remove nth node from end of list": (19, "remove-nth-node-from-end-of-list"),
    "valid parentheses": (20, "valid-parentheses"),
    "merge two sorted lists": (21, "merge-two-sorted-lists"),
    "generate parentheses": (22, "generate-parentheses"),
    "merge k sorted lists": (23, "merge-k-sorted-lists"),
    "swap nodes in pairs": (24, "swap-nodes-in-pairs"),
    "reverse nodes in k-group": (25, "reverse-nodes-in-k-group"),
    "remove duplicates from sorted array": (26, "remove-duplicates-from-sorted-array"),
    "remove element": (27, "remove-element"),
    "find the index of the first occurrence in a string": (28, "find-the-index-of-the-first-occurrence-in-a-string"),
    "divide two integers": (29, "divide-two-integers"),
    "substring with concatenation of all words": (30, "substring-with-concatenation-of-all-words"),
    "next permutation": (31, "next-permutation"),
    "longest valid parentheses": (32, "longest-valid-parentheses"),
    "search in rotated sorted array": (33, "search-in-rotated-sorted-array"),
    "find first and last position of element in sorted array": (34, "find-first-and-last-position-of-element-in-sorted-array"),
    "search insert position": (35, "search-insert-position"),
    "combination sum": (39, "combination-sum"),
    "combination sum ii": (40, "combination-sum-ii"),
    "permutations": (46, "permutations"),
    "permutations ii": (47, "permutations-ii"),
    "rotate image": (48, "rotate-image"),
    "group anagrams": (49, "group-anagrams"),
    "pow(x, n)": (50, "powx-n"),
    "n-queens": (51, "n-queens"),
    "n-queens ii": (52, "n-queens-ii"),
    "maximum subarray": (53, "maximum-subarray"),
    "spiral matrix": (54, "spiral-matrix"),
    "jump game": (55, "jump-game"),
    "jump game ii": (45, "jump-game-ii"),
    "merge intervals": (56, "merge-intervals"),
    "insert interval": (57, "insert-interval"),
    "length of last word": (58, "length-of-last-word"),
    "spiral matrix ii": (59, "spiral-matrix-ii"),
    "unique paths": (62, "unique-paths"),
    "unique paths ii": (63, "unique-paths-ii"),
    "minimum path sum": (64, "minimum-path-sum"),
    "valid number": (65, "valid-number"),
    "plus one": (66, "plus-one"),
    "add binary": (67, "add-binary"),
    "text justification": (68, "text-justification"),
    "sqrtx": (69, "sqrtx"),
    "climbing stairs": (70, "climbing-stairs"),
    "simplify path": (71, "simplify-path"),
    "edit distance": (72, "edit-distance"),
    "set matrix zeroes": (73, "set-matrix-zeroes"),
    "search a 2d matrix": (74, "search-a-2d-matrix"),
    "search a 2d matrix ii": (240, "search-a-2d-matrix-ii"),
    "largest rectangle in histogram": (84, "largest-rectangle-in-histogram"),
    "maximal rectangle": (85, "maximal-rectangle"),
    "partition list": (86, "partition-list"),
    "merge sorted array": (88, "merge-sorted-array"),
    "gray code": (89, "gray-code"),
    "restore ip addresses": (93, "restore-ip-addresses"),
    "reverse linked list ii": (92, "reverse-linked-list-ii"),
    "decode ways": (91, "decode-ways"),
    "word break": (139, "word-break"),
    "word break ii": (140, "word-break-ii"),
    "lru cache": (146, "lru-cache"),
    "evaluate reverse polish notation": (150, "evaluate-reverse-polish-notation"),
    "reverse words in a string": (151, "reverse-words-in-a-string"),
    "binary search tree iterator": (173, "binary-search-tree-iterator"),
    "two sum iii - data structure design": (170, "two-sum-iii-data-structure-design"),
    "find median from data stream": (295, "find-median-from-data-stream"),
    "implement trie (prefix tree)": (208, "implement-trie-prefix-tree"),
    "word search ii": (212, "word-search-ii"),
    "number of islands": (200, "number-of-islands"),
    "course schedule": (207, "course-schedule"),
    "course schedule ii": (210, "course-schedule-ii"),
    "minimum height trees": (310, "minimum-height-trees"),
    "alien dictionary": (269, "alien-dictionary"),
    "longest increasing subsequence": (300, "longest-increasing-subsequence"),
    "coin change": (322, "coin-change"),
    "word ladder": (127, "word-ladder"),
    "word ladder ii": (126, "word-ladder-ii"),
    "house robber": (198, "house-robber"),
    "house robber ii": (213, "house-robber-ii"),
    "house robber iii": (337, "house-robber-iii"),
    "range sum query - immutable": (303, "range-sum-query-immutable"),
    "range sum query 2d - immutable": (304, "range-sum-query-2d-immutable"),
    "range sum query 2d - mutable": (308, "range-sum-query-2d-mutable"),
    "the skyline problem": (218, "the-skyline-problem"),
    "maximal square": (221, "maximal-square"),
    "contains duplicate": (217, "contains-duplicate"),
    "contains duplicate ii": (219, "contains-duplicate-ii"),
    "contains duplicate iii": (220, "contains-duplicate-iii"),
    "valid anagram": (242, "valid-anagram"),
    "implement queue using stacks": (232, "implement-queue-using-stacks"),
    "implement stack using queues": (225, "implement-stack-using-queues"),
    "invert binary tree": (226, "invert-binary-tree"),
    "kth smallest element in a bst": (230, "kth-smallest-element-in-a-bst"),
    "lowest common ancestor of a binary search tree": (235, "lowest-common-ancestor-of-a-binary-search-tree"),
    "lowest common ancestor of a binary tree": (236, "lowest-common-ancestor-of-a-binary-tree"),
    "delete node in a linked list": (237, "delete-node-in-a-linked-list"),
    "majority element": (169, "majority-element"),
    "majority element ii": (229, "majority-element-ii"),
    "the largest number": (179, "the-largest-number"),
    "kth largest element in an array": (215, "kth-largest-element-in-an-array"),
    "find the celebrity": (277, "find-the-celebrity"),
    "happy number": (202, "happy-number"),
    "isomorphic strings": (205, "isomorphic-strings"),
    "word pattern": (290, "word-pattern"),
    "shuffle an array": (384, "shuffle-an-array"),
    "min stack": (155, "min-stack"),
    "fizz buzz": (412, "fizz-buzz"),
    "serialize and deserialize binary tree": (297, "serialize-and-deserialize-binary-tree"),
    "binary tree right side view": (199, "binary-tree-right-side-view"),
    "find peak element": (162, "find-peak-element"),
    "symmetric tree": (101, "symmetric-tree"),
    "task scheduler": (621, "task-scheduler"),
}


def now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def safe_zoneinfo(name: str) -> datetime.tzinfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return datetime.UTC


def resolve_timezone_name(config: Dict[str, Any] | None = None) -> str:
    candidate = str((config or {}).get("timezone") or DEFAULT_TIMEZONE).strip()
    try:
        ZoneInfo(candidate)
        return candidate
    except ZoneInfoNotFoundError:
        try:
            ZoneInfo(DEFAULT_TIMEZONE)
            return DEFAULT_TIMEZONE
        except ZoneInfoNotFoundError:
            return "UTC"


def planner_timezone(config: Dict[str, Any] | None = None) -> datetime.tzinfo:
    return safe_zoneinfo(resolve_timezone_name(config))


def now_in_planner_timezone(config: Dict[str, Any] | None = None) -> datetime.datetime:
    return now_utc().astimezone(planner_timezone(config))


def iso_utc(dt: datetime.datetime) -> str:
    return dt.astimezone(datetime.UTC).isoformat().replace("+00:00", "Z")


def format_local_readable(dt_str: str, timezone_name: str | None = None) -> str:
    if not dt_str:
        return "Unknown"
    try:
        dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        target_tz = safe_zoneinfo(timezone_name) if timezone_name else planner_timezone()
        local_dt = dt.astimezone(target_tz)
        return local_dt.strftime("%b %d, %Y %I:%M:%S %p %Z")
    except Exception:
        return dt_str


def emit_progress(step_index: int, step_total: int, label: str) -> None:
    print(f"[PROGRESS {step_index}/{step_total}] {label}", flush=True)


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_config():
    planner_config_path = os.path.join(PROJECT_ROOT, "config", "planner_config.json")
    fallback_config_path = os.path.join(PROJECT_ROOT, "config", "config.json")
    if os.path.exists(planner_config_path):
        return load_json(planner_config_path, {})
    return load_json(fallback_config_path, {})


def ts_to_iso(ts):
    if ts is None:
        return None
    try:
        return datetime.datetime.fromtimestamp(int(ts), tz=datetime.UTC).isoformat().replace("+00:00", "Z")
    except Exception:
        return None


def clean_env_value(name: str) -> str:
    value = os.environ.get(name, "")
    if value is None:
        return ""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1].strip()
    return value


def env_flag(name: str, default: bool) -> bool:
    value = clean_env_value(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def difficulty_score(difficulty: str) -> float:
    return {"Easy": 1.0, "Medium": 2.0, "Hard": 3.0}.get(difficulty, 1.0)


def get_gap_fill_candidates_from_config(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    normalized_by_slug = {item["slug"]: dict(item) for item in DEFAULT_GAP_FILL_CANDIDATES}
    configured = config.get("canonical_gap_candidates")
    if isinstance(configured, list) and configured:
        for item in configured:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            slug = str(item.get("slug", "")).strip()
            if not title or not slug:
                continue
            normalized_by_slug[slug] = {
                "title": title,
                "slug": slug,
                "difficulty": str(item.get("difficulty", "Medium")).strip() or "Medium",
                "reason": str(item.get("reason", "canonical interview anchor")).strip() or "canonical interview anchor",
            }
    return list(normalized_by_slug.values())


def get_review_priority_bonus(config: Dict[str, Any]) -> Dict[str, float]:
    configured = config.get("review_priority_bonus")
    bonuses: Dict[str, float] = dict(DEFAULT_REVIEW_PRIORITY_BONUS)
    if not isinstance(configured, dict):
        return bonuses
    for slug, value in configured.items():
        try:
            bonuses[str(slug).strip()] = float(value)
        except Exception:
            continue
    return bonuses


def get_review_deprioritized_slugs(config: Dict[str, Any]) -> set[str]:
    configured = config.get("review_deprioritized_slugs")
    slugs = set(DEFAULT_REVIEW_DEPRIORITIZED_SLUGS)
    if not isinstance(configured, list):
        return slugs
    for item in configured:
        slug = str(item).strip()
        if slug:
            slugs.add(slug)
    return slugs


def get_interview_core_priority_bonus(config: Dict[str, Any]) -> Dict[str, float]:
    configured = config.get("interview_core_priority_bonus")
    bonuses: Dict[str, float] = dict(INTERVIEW_CORE_PRIORITY_BONUS)
    if not isinstance(configured, dict):
        return bonuses
    for slug, value in configured.items():
        try:
            bonuses[str(slug).strip()] = float(value)
        except Exception:
            continue
    return bonuses


def solved_count_profile(solved_count: int) -> Dict[str, float]:
    if solved_count < 80:
        return {
            "review_core_multiplier": 1.15,
            "medium_gap_bonus": 1.1,
            "hard_gap_penalty": 0.9,
            "hard_anchor_threshold": 5.0,
        }
    if solved_count < 180:
        return {
            "review_core_multiplier": 1.08,
            "medium_gap_bonus": 0.55,
            "hard_gap_penalty": 0.35,
            "hard_anchor_threshold": 5.2,
        }
    return {
        "review_core_multiplier": 1.0,
        "medium_gap_bonus": 0.0,
        "hard_gap_penalty": 0.0,
        "hard_anchor_threshold": 5.4,
    }


def is_low_transfer_easy(slug: str, difficulty: str, canonical_bonus: float) -> bool:
    return difficulty == "Easy" and canonical_bonus < 2.5 and slug in LOW_TRANSFER_EASY_SLUGS


def is_generic_easy_review(difficulty: str, priority_bonus: float) -> bool:
    return difficulty == "Easy" and priority_bonus <= 0.0


def is_obscure_or_contesty(slug: str, title: str, canonical_bonus: float) -> bool:
    if canonical_bonus >= 3.0:
        return False
    haystack = f"{slug} {title}".lower()
    return any(keyword in haystack for keyword in OBSCURE_CONTEST_KEYWORDS)


def parse_snapshot_now(snapshot: Dict[str, Any]) -> datetime.datetime:
    generated_at = snapshot.get("generated_at")
    if generated_at:
        try:
            return datetime.datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        except Exception:
            pass
    return now_utc()


def age_hours_from_ts(ts: Any, ref_now: datetime.datetime) -> float:
    if ts is None:
        return float("inf")
    try:
        dt = datetime.datetime.fromtimestamp(int(ts), tz=datetime.UTC)
        return max(0.0, (ref_now - dt).total_seconds() / 3600.0)
    except Exception:
        return float("inf")


def recently_mentioned(title: str, history: List[Dict[str, Any]]) -> bool:
    if not title:
        return False
    needle = title.lower()
    for item in history:
        for field in ["tldr", "why_now", "primary_action", "secondary_action", "stretch_action"]:
            if needle in str(item.get(field, "")).lower():
                return True
    return False


def format_activity_item(item):
    if item["type"] == "new_problem_in_snapshot":
        return {
            "type": item["type"],
            "title": item["title"],
            "slug": item["slug"],
            "current_last_ts": item.get("current_last_ts"),
            "current_last_ts_iso": ts_to_iso(item.get("current_last_ts")),
            "current_count": item.get("current_count"),
        }

    if item["type"] == "timestamp_changed":
        return {
            "type": item["type"],
            "title": item["title"],
            "slug": item["slug"],
            "old_last_ts": item.get("old_last_ts"),
            "old_last_ts_iso": ts_to_iso(item.get("old_last_ts")),
            "new_last_ts": item.get("new_last_ts"),
            "new_last_ts_iso": ts_to_iso(item.get("new_last_ts")),
            "old_count": item.get("old_count"),
            "new_count": item.get("new_count"),
        }

    if item["type"] == "count_changed":
        return {
            "type": item["type"],
            "title": item["title"],
            "slug": item["slug"],
            "last_ts": item.get("last_ts"),
            "last_ts_iso": ts_to_iso(item.get("last_ts")),
            "old_count": item.get("old_count"),
            "new_count": item.get("new_count"),
        }

    return item


def build_headers():
    session = clean_env_value("LEETCODE_SESSION")
    csrftoken = clean_env_value("LEETCODE_CSRFTOKEN")

    cookie_parts = []
    if session:
        cookie_parts.append(f"LEETCODE_SESSION={session}")
    if csrftoken:
        cookie_parts.append(f"csrftoken={csrftoken}")

    headers = {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com/problemset/",
        "User-Agent": "Mozilla/5.0",
    }

    if cookie_parts:
        headers["Cookie"] = "; ".join(cookie_parts)
    if csrftoken:
        headers["x-csrftoken"] = csrftoken

    return headers


def post_graphql(query, variables=None, timeout=30, max_retries=3):
    headers = build_headers()
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                GRAPHQL_URL,
                json={"query": query, "variables": variables or {}},
                headers=headers,
                timeout=timeout,
            )

            try:
                payload = resp.json()
            except Exception:
                raise RuntimeError(
                    f"GraphQL response was not valid JSON. "
                    f"status={resp.status_code}, text={resp.text[:500]}"
                )

            if resp.status_code >= 400:
                raise RuntimeError(
                    f"GraphQL HTTP error. status={resp.status_code}, payload={payload}"
                )

            if "errors" in payload:
                raise RuntimeError(f"GraphQL returned errors: {payload['errors']}")

            if "data" not in payload:
                raise RuntimeError(f"GraphQL did not return data. Payload: {payload}")

            return payload["data"]

        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            if attempt < max_retries:
                wait_seconds = [2, 5, 10][attempt - 1] if attempt - 1 < 3 else 10
                print(
                    f"LeetCode request attempt {attempt}/{max_retries} failed with a network timeout/connection issue. "
                    f"Retrying in {wait_seconds}s..."
                )
                time.sleep(wait_seconds)
                continue

            raise RuntimeError(
                "LeetCode timed out while fetching data after multiple retries. "
                "This is usually temporary. Check your connection and try rerunning in a minute."
            ) from e

        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < max_retries:
                wait_seconds = [2, 5, 10][attempt - 1] if attempt - 1 < 3 else 10
                print(
                    f"LeetCode request attempt {attempt}/{max_retries} failed with a request error. "
                    f"Retrying in {wait_seconds}s..."
                )
                time.sleep(wait_seconds)
                continue

            raise RuntimeError(
                "LeetCode request failed after multiple retries. "
                "Please try again shortly."
            ) from e

    raise RuntimeError(
        f"LeetCode request failed unexpectedly after retries. Last error: {last_error}"
    )


def verify_env_setup():
    if not os.path.exists(ENV_PATH):
        raise RuntimeError(missing_env_file_message(Path(ENV_PATH)))

    missing = [name for name in ("OPENAI_API_KEY", "LEETCODE_SESSION", "LEETCODE_CSRFTOKEN") if not clean_env_value(name)]
    if missing:
        raise RuntimeError(missing_credentials_message(missing, Path(ENV_PATH)))

    print(f".env file exists: {os.path.exists(ENV_PATH)}")
    print(f"OPENAI_API_KEY present: {bool(clean_env_value('OPENAI_API_KEY'))}")
    print(f"LEETCODE_SESSION present: {bool(clean_env_value('LEETCODE_SESSION'))}")
    print(f"LEETCODE_CSRFTOKEN present: {bool(clean_env_value('LEETCODE_CSRFTOKEN'))}")


def verify_leetcode_auth():
    query = """
    query globalData {
      userStatus {
        isSignedIn
      }
    }
    """

    session = clean_env_value("LEETCODE_SESSION")
    csrftoken = clean_env_value("LEETCODE_CSRFTOKEN")

    if not session:
        raise RuntimeError("LeetCode auth failed: LEETCODE_SESSION is missing or empty.")
    if not csrftoken:
        raise RuntimeError("LeetCode auth failed: LEETCODE_CSRFTOKEN is missing or empty.")

    data = post_graphql(query, {}, timeout=20)
    status = data.get("userStatus") or {}

    print(f"LeetCode signed in: {status.get('isSignedIn')}")

    if not status.get("isSignedIn"):
        raise RuntimeError(
            "LeetCode auth failed: cookies were sent, but LeetCode still reports not signed in. "
            "Refresh LEETCODE_SESSION and LEETCODE_CSRFTOKEN from your logged-in browser session."
        )


def get_solved_questions():
    query_all = """
    query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
      problemsetQuestionList: questionList(
        categorySlug: $categorySlug
        limit: $limit
        skip: $skip
        filters: $filters
      ) {
        total: totalNum
        questions: data {
          title
          titleSlug
          difficulty
          status
          frontendQuestionId: questionFrontendId
          isPaidOnly
        }
      }
    }
    """

    all_questions = []
    skip = 0
    page_size = 100

    while True:
        data = post_graphql(
            query_all,
            {
                "categorySlug": "",
                "skip": skip,
                "limit": page_size,
                "filters": {},
            },
            timeout=30,
        )

        block = data["problemsetQuestionList"]
        questions = block["questions"]

        if not questions:
            break

        all_questions.extend(questions)
        print(f"Fetched {len(questions)} questions at skip={skip}. Total so far: {len(all_questions)}")

        if len(questions) < page_size:
            break

        skip += page_size

    by_slug = {}
    for q in all_questions:
        by_slug[q["titleSlug"]] = q

    deduped = list(by_slug.values())
    solved = [q for q in deduped if q.get("status") == "ac"]

    print(f"Total questions fetched: {len(deduped)}")
    print(f"Total solved questions found: {len(solved)}")

    if len(deduped) > 0 and len(solved) == 0:
        raise RuntimeError(
            "LeetCode auth looks suspicious: the public problem list loaded, but zero solved problems were returned. "
            "This usually means your cookies are missing, expired, or not being loaded correctly."
        )

    return solved


def get_problem_submission_stats(slug):
    query_sub = """
    query submissionList($offset: Int!, $limit: Int!, $lastKey: String, $questionSlug: String!) {
      submissionList(offset: $offset, limit: $limit, lastKey: $lastKey, questionSlug: $questionSlug) {
        lastKey
        hasNext
        submissions {
          timestamp
          statusDisplay
        }
      }
    }
    """

    try:
        data = post_graphql(
            query_sub,
            {
                "offset": 0,
                "limit": 20,
                "lastKey": None,
                "questionSlug": slug,
            },
            timeout=30,
        )

        sub_block = data["submissionList"]
        submissions = sub_block.get("submissions", []) or []
        accepted = [s for s in submissions if s.get("statusDisplay") == "Accepted"]

        last_ts = None
        if accepted:
            try:
                last_ts = max(int(s["timestamp"]) for s in accepted if s.get("timestamp"))
            except Exception:
                last_ts = None

        return {
            "last_ts": last_ts,
            "count": len(accepted) if accepted else None,
            "ok": True,
            "error": None,
        }

    except Exception as e:
        return {
            "last_ts": None,
            "count": None,
            "ok": False,
            "error": str(e),
        }


def generate_real_snapshot(prev_snapshot=None):
    prev_snapshot = prev_snapshot or {}
    prev_by_slug = {
        p.get("slug"): p
        for p in prev_snapshot.get("problems", [])
        if p.get("slug")
    }

    solved = get_solved_questions()
    problems = []
    timestamp_failures = []

    for q in solved:
        slug = q["titleSlug"]
        prev = prev_by_slug.get(slug, {})

        stats = get_problem_submission_stats(slug)

        last_ts = stats["last_ts"]
        count = stats["count"]

        if last_ts is None:
            last_ts = prev.get("last_ts")
        if count is None:
            count = prev.get("count", 1)

        if not stats["ok"]:
            timestamp_failures.append({
                "slug": slug,
                "title": q["title"],
                "error": stats["error"],
            })

        problems.append({
            "title": q["title"],
            "slug": slug,
            "frontend_id": q["frontendQuestionId"],
            "difficulty": q["difficulty"],
            "last_ts": last_ts,
            "count": count,
        })

    problems.sort(
        key=lambda p: int(p["frontend_id"]) if str(p["frontend_id"]).isdigit() else 10**9
    )

    return {
        "generated_at": iso_utc(now_utc()),
        "problem_count": len(problems),
        "timestamp_failures_count": len(timestamp_failures),
        "timestamp_failures_sample": timestamp_failures[:10],
        "problems": problems,
    }


def diff(prev, cur):
    prev_problems = prev.get("problems", [])
    cur_problems = cur.get("problems", [])

    if not prev_problems:
        return {
            "status": "initial_run",
            "items": [],
            "message": "Initial run. No prior snapshot to diff against."
        }

    prev_count = len(prev_problems)
    cur_count = len(cur_problems)

    prev_by_slug = {p["slug"]: p for p in prev_problems if p.get("slug")}
    changed = []
    new_problem_items = []

    for p in cur_problems:
        slug = p.get("slug")
        if not slug:
            continue

        old = prev_by_slug.get(slug)
        if old is None:
            new_problem_items.append({
                "type": "new_problem_in_snapshot",
                "slug": slug,
                "title": p["title"],
                "current_last_ts": p.get("last_ts"),
                "current_count": p.get("count"),
            })
            continue

        if p.get("last_ts") != old.get("last_ts"):
            changed.append({
                "type": "timestamp_changed",
                "slug": slug,
                "title": p["title"],
                "old_last_ts": old.get("last_ts"),
                "new_last_ts": p.get("last_ts"),
                "old_count": old.get("count"),
                "new_count": p.get("count"),
            })
        elif p.get("count") != old.get("count"):
            changed.append({
                "type": "count_changed",
                "slug": slug,
                "title": p["title"],
                "last_ts": p.get("last_ts"),
                "old_count": old.get("count"),
                "new_count": p.get("count"),
            })

    if cur_count > int(prev_count * 1.25):
        return {
            "status": "snapshot_rebaseline",
            "items": [format_activity_item(x) for x in new_problem_items[:20]],
            "message": (
                f"Snapshot expanded from {prev_count} to {cur_count} problems. "
                "Treating this run as a rebaseline, not true recent user activity."
            ),
        }

    if not changed and not new_problem_items:
        return {
            "status": "no_new_activity",
            "items": [],
            "message": "No new LeetCode activity detected since last snapshot."
        }

    all_items = changed + new_problem_items
    return {
        "status": "activity_detected",
        "items": [format_activity_item(x) for x in all_items[:20]],
        "message": f"{len(all_items)} changed problem(s) since last snapshot."
    }


def summarize_snapshot(snapshot):
    problems = snapshot.get("problems", [])
    easy = sum(1 for p in problems if p.get("difficulty") == "Easy")
    medium = sum(1 for p in problems if p.get("difficulty") == "Medium")
    hard = sum(1 for p in problems if p.get("difficulty") == "Hard")
    with_ts = sum(1 for p in problems if p.get("last_ts") is not None)

    return {
        "problem_count": len(problems),
        "difficulty_breakdown": {
            "Easy": easy,
            "Medium": medium,
            "Hard": hard,
        },
        "timestamp_coverage": {
            "with_last_ts": with_ts,
            "without_last_ts": len(problems) - with_ts,
        },
        "timestamp_failures_count": snapshot.get("timestamp_failures_count", 0),
    }


def get_existing_run_dirs():
    return sorted([
        d for d in os.listdir(HISTORY_DIR)
        if os.path.isdir(os.path.join(HISTORY_DIR, d))
    ])


def get_recent_plan_memory():
    history_plans = []
    run_dirs = get_existing_run_dirs()
    for d in run_dirs:
        plan_path = os.path.join(HISTORY_DIR, d, "plan_memory.json")
        if os.path.exists(plan_path):
            history_plans.append(load_json(plan_path, {}))
    return history_plans


def get_target_shape(config: Dict[str, Any]) -> Dict[str, int]:
    planning_bias = config.get("planning_bias", "balanced_growth")
    if planning_bias == "interview_maintenance":
        return {"review": 3, "gap_fill": 1, "fragile": 0}
    if planning_bias == "aggressive_gap_fill":
        return {"review": 1, "gap_fill": 3, "fragile": 0}
    return {"review": 2, "gap_fill": 2, "fragile": 0}


def build_candidate_pools(snapshot: Dict[str, Any], history: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    problems = snapshot.get("problems", [])
    solved_slugs = {p.get("slug") for p in problems if p.get("slug")}
    ref_now = parse_snapshot_now(snapshot)
    review_priority_bonus = get_review_priority_bonus(config)
    review_deprioritized_slugs = get_review_deprioritized_slugs(config)
    interview_core_bonus = get_interview_core_priority_bonus(config)
    profile = solved_count_profile(len(problems))

    review_candidates = []
    fragile_candidates = []
    cooldown_excluded = []

    for p in problems:
        slug = p.get("slug")
        title = p.get("title")
        difficulty = p.get("difficulty")
        last_ts = p.get("last_ts")
        count = p.get("count", 1) or 1

        age_hours = age_hours_from_ts(last_ts, ref_now)

        if age_hours < COOLDOWN_HOURS:
            cooldown_excluded.append({
                "title": title,
                "slug": slug,
                "difficulty": difficulty,
                "count": count,
                "age_hours": round(age_hours, 1),
                "reason": "solved within last 24 hours",
            })
            continue

        canonical_bonus = CANONICAL_REVIEW_BONUS.get(slug, 0.0)
        interview_bonus = interview_core_bonus.get(slug, 0.0)
        priority_bonus = max(review_priority_bonus.get(slug, canonical_bonus), interview_bonus)
        deprioritized_penalty = 4.5 if slug in review_deprioritized_slugs else 0.0
        generic_easy_penalty = 4.0 if is_generic_easy_review(difficulty, priority_bonus) else 0.0
        low_transfer_easy_penalty = 2.5 if is_low_transfer_easy(slug, difficulty, canonical_bonus) else 0.0
        obscure_penalty = 2.0 if is_obscure_or_contesty(slug, title, canonical_bonus) else 0.0
        recent_plan_penalty = 1.0 if recently_mentioned(title, history) else 0.0
        stage_review_bonus = interview_bonus * profile["review_core_multiplier"] if count <= 2 else interview_bonus * 0.5
        age_component = min(age_hours / 24.0, 365.0) * 0.03
        low_count_component = max(0, 3 - min(count, 3)) * 2.0
        difficulty_component = difficulty_score(difficulty) * 1.2
        review_score = (
            age_component +
            low_count_component +
            difficulty_component +
            priority_bonus +
            stage_review_bonus -
            deprioritized_penalty -
            generic_easy_penalty -
            low_transfer_easy_penalty -
            obscure_penalty -
            recent_plan_penalty
        )

        review_candidates.append({
            "title": title,
            "slug": slug,
            "difficulty": difficulty,
            "count": count,
            "last_ts": last_ts,
            "last_ts_iso": ts_to_iso(last_ts),
            "age_hours": round(age_hours, 1),
            "score": round(review_score, 2),
            "score_components": {
                "age": round(age_component, 2),
                "low_count": round(low_count_component, 2),
                "difficulty": round(difficulty_component, 2),
                "priority_bonus": priority_bonus,
                "interview_core_bonus": interview_bonus,
                "stage_review_bonus": round(stage_review_bonus, 2),
                "canonical_bonus": canonical_bonus,
                "deprioritized_penalty": deprioritized_penalty,
                "generic_easy_penalty": generic_easy_penalty,
                "low_transfer_easy_penalty": low_transfer_easy_penalty,
                "obscure_penalty": obscure_penalty,
                "recent_plan_penalty": recent_plan_penalty,
            },
            "why": "old + low-count solved problem with interview value; explicit canonical anchors preferred over noisy stale problems",
        })

        if FRAGILE_MIN_HOURS <= age_hours <= FRAGILE_MAX_DAYS * 24 and count <= 2:
            fragile_score = (
                (FRAGILE_MAX_DAYS * 24 - age_hours) * 0.02 +
                (3 - min(count, 3)) * 1.5 +
                difficulty_score(difficulty) * 0.7
            )
            fragile_candidates.append({
                "title": title,
                "slug": slug,
                "difficulty": difficulty,
                "count": count,
                "last_ts": last_ts,
                "last_ts_iso": ts_to_iso(last_ts),
                "age_hours": round(age_hours, 1),
                "score": round(fragile_score, 2),
                "why": "recent but outside cooldown and still low-count / fragile",
            })

    review_candidates.sort(key=lambda x: (-x["score"], x["age_hours"]))
    fragile_candidates.sort(key=lambda x: (-x["score"], x["age_hours"]))

    gap_fill_candidates = []
    for item in get_gap_fill_candidates_from_config(config):
        if item["slug"] in solved_slugs:
            continue

        recent_penalty = 1.5 if recently_mentioned(item["title"], history) else 0.0
        interview_bonus = interview_core_bonus.get(item["slug"], 0.0)
        medium_stage_bonus = profile["medium_gap_bonus"] if item["difficulty"] == "Medium" else 0.0
        hard_stage_penalty = 0.0
        if item["difficulty"] == "Hard" and profile["hard_gap_penalty"] > 0:
            hard_stage_penalty = profile["hard_gap_penalty"]
            if interview_bonus >= profile["hard_anchor_threshold"]:
                hard_stage_penalty *= 0.35
        score = (
            difficulty_score(item["difficulty"]) * 1.5 +
            interview_bonus * 1.4 +
            medium_stage_bonus -
            hard_stage_penalty -
            recent_penalty
        )

        gap_fill_candidates.append({
            "title": item["title"],
            "slug": item["slug"],
            "difficulty": item["difficulty"],
            "score": round(score, 2),
            "score_components": {
                "difficulty": round(difficulty_score(item["difficulty"]) * 1.5, 2),
                "interview_core_bonus": round(interview_bonus * 1.4, 2),
                "medium_stage_bonus": round(medium_stage_bonus, 2),
                "hard_stage_penalty": round(hard_stage_penalty, 2),
                "recent_plan_penalty": recent_penalty,
            },
            "why": item["reason"],
            "recently_mentioned": recently_mentioned(item["title"], history),
        })

    gap_fill_candidates.sort(key=lambda x: (-x["score"], x["title"]))

    return {
        "review_candidates": review_candidates[:12],
        "gap_fill_candidates": gap_fill_candidates[:16],
        "fragile_candidates": fragile_candidates[:6],
        "cooldown_excluded": cooldown_excluded[:12],
    }


def build_prompt(
    snapshot: Dict[str, Any],
    delta: Dict[str, Any],
    history: List[Dict[str, Any]],
    run_id: str,
    config: Dict[str, Any],
    target_shape: Dict[str, int],
    candidate_pools: Dict[str, Any],
):
    summary = summarize_snapshot(snapshot)

    history_days = int(config.get("history_days", 7))
    max_primary_review_problems = int(config.get("max_primary_review_problems", 4))
    recent_history = history[-history_days:]
    planning_bias = config.get("planning_bias", "balanced_growth")

    recent_activity_section = {
        "status": delta["status"],
        "message": delta["message"],
        "items": delta["items"],
    }

    return f'''You are planning LeetCode practice.

SYSTEM GOAL:
Pick the smallest high-impact session that improves interview readiness.

IMPORTANT ARCHITECTURE:
Python has already done the deterministic parts:
- applied the planning bias
- computed the target shape
- excluded very recent cooldown problems from redo pools
- generated candidate pools for review, gap fill, and fragile reinforcement

Your job is the smart part:
- choose the final plan from the candidate pools
- respect the target shape unless there is a truly strong reason not to
- explain any deviation clearly
- produce user-facing explanations, not planner-internal justifications

PLANNING BIAS:
Current mode is "{planning_bias}".

TARGET SHAPE FOR THIS RUN:
- Review problems: {target_shape["review"]}
- Gap-fill problems: {target_shape["gap_fill"]}
- Fragile reinforcement problems: {target_shape["fragile"]}

CORE PRINCIPLE:
Balanced does NOT mean equal representation.
Do NOT force symmetry across categories beyond the target shape.

CANDIDATE POOLS:
Review candidates:
{candidate_pools["review_candidates"]}

Gap-fill candidates:
{candidate_pools["gap_fill_candidates"]}

Fragile candidates:
{candidate_pools["fragile_candidates"]}

Cooldown excluded:
{candidate_pools["cooldown_excluded"]}

RULES:
- Prefer choosing from the candidate pools above.
- Do NOT recommend anything in cooldown_excluded as a redo today.
- If you deviate from the target shape, explain why explicitly.
- Fragile reinforcement is optional and should only be used if clearly valuable.
- Prefer the smallest strong session.
- Never exceed {max_primary_review_problems} items in Primary.
- Total workload should usually stay around 4–5 problems.

TLDR RULE:
- TLDR must be direct instructions.
- It must list exact problems to do in order.
- Keep it concise.
- TLDR order must match Primary → Secondary → Stretch.
- TLDR must be a newline-separated string with exactly one problem per line.
- Each TLDR line must be numbered in order like:
  1. Find Minimum in Rotated Sorted Array
  2. 3Sum
  3. Daily Temperatures
  4. Minimum Window Substring
- Do NOT write a prose sentence like "Do these 4 in order: A, B, C, D."
- Do NOT put multiple problems on one line.

NO ACTIVITY RULE:
If there is no new activity, keep the core recommendations stable.
Do not change problems just for variety.

IMPORTANT NOTES:
- Use "generated_at" as the current reference time for recency comparisons.
- Use timestamps and counts heavily.
- Treat old + low count as weak mastery.
- Output ONLY valid JSON.

USER EXPLANATION RULES:
- why_now_summary must be short, concrete, and user-facing.
- Explain the user's weaknesses and gaps, not planner mechanics.
- Avoid phrases like "target shape", "stability beats swapping", "current pool", or "no reason to rotate".
- problem_reasons must contain one short reason per chosen problem, in the same order as the TLDR.
- Each problem reason should explain the actual leverage of that problem: stale recall risk, weak mastery, missing canonical pattern, or important interview coverage gap.

Snapshot summary:
{summary}

Recent activity:
{recent_activity_section}

Recent plan memory:
{recent_history}

Current problems:
{snapshot["problems"]}

Return JSON with exactly this shape:
{{
  "run_id": "{run_id}",
  "generated_at": "{iso_utc(now_utc())}",
  "date": "{now_in_planner_timezone(config).date().isoformat()}",
  "tldr": "1. Find Minimum in Rotated Sorted Array\n2. 3Sum\n3. Daily Temperatures\n4. Minimum Window Substring",
  "why_now_summary": "...",
  "problem_reasons": [
    "...",
    "..."
  ],
  "primary_action": "...",
  "secondary_action": "...",
  "stretch_action": "...",
  "do_not_focus_on": [
    "..."
  ],
  "reasoning": {{
    "summary": "...",
    "detailed": "..."
  }},
  "insights": [
    "...",
    "..."
  ],
  "focus_mode": "review|new_learning|mixed",
  "confidence": "high|medium|low"
}}
'''


def summarize_openai_error(status_code: int, data: Dict[str, Any]) -> str:
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        message = str(error.get("message") or "").strip()
        error_type = str(error.get("type") or "").strip()
        error_code = str(error.get("code") or "").strip()
        message_lower = message.lower()
        code_lower = error_code.lower()
        type_lower = error_type.lower()

        if (
            "insufficient_quota" in code_lower
            or "insufficient" in message_lower
            or "quota" in message_lower
            or "billing" in message_lower
            or "insufficient_quota" in type_lower
        ):
            return (
                "OpenAI request failed because the API account has no available balance or quota. "
                "Add billing or credits to your OpenAI account and rerun the planner."
            )

        if resp_status_is_auth(status_code, error_code, error_type, message_lower):
            return (
                "OpenAI request failed because the API key was rejected. "
                "Check OPENAI_API_KEY and confirm it is valid for the Responses API."
            )

        detail = message or f"type={error_type or 'unknown'}, code={error_code or 'unknown'}"
        return f"OpenAI API error (status={status_code}): {detail}"

    return f"OpenAI API error. status={status_code}, payload={data}"


def resp_status_is_auth(status_code: int, error_code: str, error_type: str, message_lower: str) -> bool:
    if status_code in (401, 403):
        return True
    return any(
        token in (error_code or "").lower() or token in (error_type or "").lower() or token in message_lower
        for token in ["invalid_api_key", "authentication", "auth", "unauthorized", "forbidden"]
    )


def enrich_plan_with_problem_metadata(plan_json: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
    """Add problem_metadata (frontend_id, slug) to plan_json based on TLDR titles"""
    tldr = plan_json.get("tldr", "")
    if not tldr:
        return

    def extract_titles() -> List[str]:
        titles: List[str] = []
        for raw_line in str(tldr).splitlines():
            line = raw_line.strip()
            line = re.sub(r"^\d+\.\s*", "", line)
            title = re.sub(r"^(Redo|Learn)\s+", "", line, flags=re.IGNORECASE).strip().rstrip(".")
            if title:
                titles.append(title)

        if len(titles) == 1:
            single = titles[0]
            intro_match = re.match(r"^(?:do|solve|work on)\b.+?:\s*(.+)$", single, flags=re.IGNORECASE)
            if intro_match:
                parts = [part.strip().rstrip(".") for part in intro_match.group(1).split(",") if part.strip()]
                if len(parts) >= 2:
                    titles = parts

        if len(titles) <= 1:
            reason_titles: List[str] = []
            for reason in plan_json.get("problem_reasons", []):
                match = re.match(r"^\s*(.+?)\s*:", str(reason).strip())
                if match:
                    title = match.group(1).strip().rstrip(".")
                    if title:
                        reason_titles.append(title)
            if len(reason_titles) >= 2:
                titles = reason_titles

        deduped: List[str] = []
        seen = set()
        for title in titles:
            if title.lower() in seen:
                continue
            seen.add(title.lower())
            deduped.append(title)
        return deduped

    # Build a title->problem mapping from snapshot (case-insensitive)
    snapshot_problems = snapshot.get("problems", [])
    title_to_problem = {p.get("title", "").lower().strip(): p for p in snapshot_problems}

    problem_metadata = {}
    for title in extract_titles():
        # Try exact match first (case-insensitive) from snapshot
        title_lower = title.lower().strip()
        problem = title_to_problem.get(title_lower)

        # If no exact match, try fuzzy matching in snapshot
        if not problem:
            for snapshot_title, snapshot_problem in title_to_problem.items():
                if title_lower in snapshot_title or snapshot_title in title_lower:
                    problem = snapshot_problem
                    break

        # If still no match, try the internal PROBLEM_LOOKUP
        if not problem:
            lookup_data = PROBLEM_LOOKUP.get(title_lower)
            if lookup_data:
                frontend_id, slug = lookup_data
                problem_metadata[title] = {
                    "frontend_id": frontend_id,
                    "slug": slug,
                }
                continue

        # If found in snapshot, use it
        if problem:
            problem_metadata[title] = {
                "frontend_id": problem.get("frontend_id", ""),
                "slug": problem.get("slug", ""),
            }
    
    if problem_metadata:
        plan_json["problem_metadata"] = problem_metadata


def validate_tldr_format(tldr: Any, problem_reasons: Any) -> None:
    value = str(tldr or "").strip()
    if not value:
        raise RuntimeError("OpenAI JSON field 'tldr' must not be empty.")

    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("OpenAI JSON field 'tldr' must contain at least one task line.")

    if len(lines) == 1 and re.search(r"\b(do|solve|work on)\b.+?:", lines[0], flags=re.IGNORECASE):
        raise RuntimeError(
            "OpenAI JSON field 'tldr' used prose summary format. "
            "It must be newline-separated with one numbered problem per line."
        )

    for idx, line in enumerate(lines, start=1):
        if not re.match(rf"^{idx}\.\s+\S", line):
            raise RuntimeError(
                "OpenAI JSON field 'tldr' must use numbered lines in order, "
                "for example '1. Find Minimum in Rotated Sorted Array'."
            )
        content = re.sub(r"^\d+\.\s*", "", line).strip()
        if len(lines) > 1 and "," in content:
            raise RuntimeError(
                "OpenAI JSON field 'tldr' must contain one problem per line, "
                "not comma-separated multiple problems on the same line."
            )

    if isinstance(problem_reasons, list) and problem_reasons and len(problem_reasons) != len(lines):
        raise RuntimeError(
            "OpenAI JSON field 'problem_reasons' must have the same number of items as TLDR lines."
        )


def call_openai_for_plan(prompt: str) -> Dict[str, Any]:
    api_key = clean_env_value("OPENAI_API_KEY")
    model = clean_env_value("OPENAI_MODEL") or "gpt-5.4"

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": model,
        "input": prompt,
        "reasoning": {
            "effort": "medium"
        }
    }

    resp = requests.post(
        OPENAI_RESPONSES_URL,
        headers=headers,
        json=payload,
        timeout=120,
    )

    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(
            f"OpenAI response was not valid JSON. status={resp.status_code}, text={resp.text[:1000]}"
        )

    if resp.status_code >= 400:
        raise RuntimeError(summarize_openai_error(resp.status_code, data))

    text_parts: List[str] = []
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text_parts.append(content.get("text", ""))

    raw_text = "\\n".join(text_parts).strip()
    if not raw_text:
        raise RuntimeError(f"OpenAI returned no output_text. Payload={data}")

    try:
        parsed = json.loads(raw_text)
    except Exception:
        raise RuntimeError(
            "OpenAI output was not valid JSON. "
            f"Raw output was: {raw_text[:2000]}"
        )

    required_top = [
        "run_id",
        "generated_at",
        "date",
        "tldr",
        "why_now_summary",
        "problem_reasons",
        "primary_action",
        "secondary_action",
        "stretch_action",
        "do_not_focus_on",
        "reasoning",
        "insights",
        "focus_mode",
        "confidence",
    ]
    for key in required_top:
        if key not in parsed:
            raise RuntimeError(f"OpenAI JSON missing required field: {key}")

    if not isinstance(parsed.get("reasoning"), dict):
        raise RuntimeError("OpenAI JSON field 'reasoning' must be an object.")

    if "summary" not in parsed["reasoning"] or "detailed" not in parsed["reasoning"]:
        raise RuntimeError("OpenAI JSON field 'reasoning' must contain 'summary' and 'detailed'.")

    if not isinstance(parsed.get("do_not_focus_on"), list):
        raise RuntimeError("OpenAI JSON field 'do_not_focus_on' must be a list.")

    if not isinstance(parsed.get("insights"), list):
        raise RuntimeError("OpenAI JSON field 'insights' must be a list.")

    if not isinstance(parsed.get("problem_reasons"), list):
        raise RuntimeError("OpenAI JSON field 'problem_reasons' must be a list.")

    validate_tldr_format(parsed.get("tldr"), parsed.get("problem_reasons"))

    if not parsed.get("why_now"):
        parsed["why_now"] = parsed.get("why_now_summary", "")

    return parsed


def make_readable_plan_text(plan_json: Dict[str, Any]) -> str:
    do_not_focus = plan_json.get("do_not_focus_on", [])
    insights = plan_json.get("insights", [])

    generated_at_utc = plan_json.get("generated_at")
    generated_at_local = format_local_readable(generated_at_utc, plan_json.get("timezone"))

    return f'''🔥 Daily LeetCode Plan

Generated (Local): {generated_at_local}
Generated (UTC): {generated_at_utc}
Run ID: {plan_json.get("run_id")}

━━━━━━━━━━━━━━━━━━━━

TLDR (DO THIS):
{plan_json.get("tldr")}

━━━━━━━━━━━━━━━━━━━━

Primary:
{plan_json.get("primary_action")}

Secondary:
{plan_json.get("secondary_action")}

Stretch:
{plan_json.get("stretch_action")}

━━━━━━━━━━━━━━━━━━━━

Why:
{plan_json.get("why_now_summary") or plan_json.get("why_now")}

Problem Reasons:
{chr(10).join("- " + str(x) for x in plan_json.get("problem_reasons", [])) if plan_json.get("problem_reasons") else "- None"}

━━━━━━━━━━━━━━━━━━━━

Avoid:
{chr(10).join("- " + str(x) for x in do_not_focus) if do_not_focus else "- None"}

━━━━━━━━━━━━━━━━━━━━

Focus Mode: {plan_json.get("focus_mode")}
Confidence: {plan_json.get("confidence")}

━━━━━━━━━━━━━━━━━━━━

Insights:
{chr(10).join("- " + str(x) for x in insights) if insights else "- None"}

━━━━━━━━━━━━━━━━━━━━

Reasoning (Short):
{plan_json.get("reasoning", {}).get("summary")}
'''


def main():
    emit_progress(1, 6, "Validating environment and LeetCode authentication")
    verify_env_setup()
    verify_leetcode_auth()

    config = load_config()
    existing_run_dirs = get_existing_run_dirs()
    prev_snapshot = {}

    if existing_run_dirs:
        latest_run = existing_run_dirs[-1]
        prev_snapshot_path = os.path.join(HISTORY_DIR, latest_run, "snapshot.json")
        prev_snapshot = load_json(prev_snapshot_path, {})

    now = now_in_planner_timezone(config)
    run_id = now.strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(HISTORY_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    snapshot_path = os.path.join(run_dir, "snapshot.json")
    prompt_path = os.path.join(run_dir, "prompt.txt")
    recommendation_path = os.path.join(run_dir, "recommendation.json")
    readable_plan_path = os.path.join(run_dir, "recommendation.txt")
    plan_memory_path = os.path.join(run_dir, "plan_memory.json")
    candidate_buckets_path = os.path.join(run_dir, "candidate_buckets.json")

    emit_progress(2, 6, "Fetching solved problems and building snapshot")
    snapshot = generate_real_snapshot(prev_snapshot=prev_snapshot)
    delta = diff(prev_snapshot, snapshot)

    print("Snapshot problem_count:", snapshot.get("problem_count"))
    if snapshot.get("problems"):
        print("Min frontend_id:", snapshot["problems"][0].get("frontend_id"))
        print("Max frontend_id:", snapshot["problems"][-1].get("frontend_id"))

    emit_progress(3, 6, "Scoring review and gap-fill candidates")
    history_plans = get_recent_plan_memory()
    target_shape = get_target_shape(config)
    candidate_pools = build_candidate_pools(snapshot, history_plans, config)

    save_json(snapshot_path, snapshot)
    save_json(candidate_buckets_path, {
        "planning_bias": config.get("planning_bias", "balanced_growth"),
        "target_shape": target_shape,
        "candidate_pools": candidate_pools,
    })

    emit_progress(4, 6, "Preparing GPT planning prompt")
    prompt = build_prompt(
        snapshot=snapshot,
        delta=delta,
        history=history_plans,
        run_id=run_id,
        config=config,
        target_shape=target_shape,
        candidate_pools=candidate_pools,
    )

    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    emit_progress(5, 6, "Generating final recommendation with GPT")
    plan_json = call_openai_for_plan(prompt)
    plan_json["timezone"] = resolve_timezone_name(config)
    plan_json["date"] = now.date().isoformat()
    
    # Enrich plan with problem metadata (frontend_id, slug)
    enrich_plan_with_problem_metadata(plan_json, snapshot)

    emit_progress(6, 6, "Saving artifacts and final readable plan")
    save_json(recommendation_path, plan_json)
    save_json(plan_memory_path, plan_json)

    readable = make_readable_plan_text(plan_json)
    with open(readable_plan_path, "w", encoding="utf-8") as f:
        f.write(readable)

    print()
    print("Primary:", plan_json.get("primary_action"))
    print("Secondary:", plan_json.get("secondary_action"))
    print("Stretch:", plan_json.get("stretch_action"))
    print("Focus mode:", plan_json.get("focus_mode"))
    print("Confidence:", plan_json.get("confidence"))

    if env_flag("LEETLOOP_OPEN_BROWSER", True):
        webbrowser.open(f"file://{os.path.abspath(readable_plan_path)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print()
        print("Pipeline failed.")
        print(str(e))
        sys.exit(1)
