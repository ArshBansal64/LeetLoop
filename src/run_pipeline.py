from dotenv import load_dotenv

from collections import Counter
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
PROJECT_ROOT = os.path.abspath(os.environ.get("LEETLOOP_HOME") or os.path.join(BASE_DIR, ".."))
RESOURCE_ROOT = os.path.abspath(os.environ.get("LEETLOOP_RESOURCE_ROOT") or PROJECT_ROOT)
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
SOLVE_SESSION_WINDOW_MINUTES = 45

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
    {"title": "Binary Tree Level Order Traversal", "slug": "binary-tree-level-order-traversal", "difficulty": "Medium", "reason": "core BFS tree traversal pattern"},
    {"title": "Lowest Common Ancestor of a Binary Tree", "slug": "lowest-common-ancestor-of-a-binary-tree", "difficulty": "Medium", "reason": "classic recursive tree interview anchor"},
    {"title": "Subarray Sum Equals K", "slug": "subarray-sum-equals-k", "difficulty": "Medium", "reason": "important prefix-sum hashmap pattern"},
    {"title": "Find All Anagrams in a String", "slug": "find-all-anagrams-in-a-string", "difficulty": "Medium", "reason": "canonical fixed-window string pattern"},
    {"title": "Search in Rotated Sorted Array", "slug": "search-in-rotated-sorted-array", "difficulty": "Medium", "reason": "flagship rotated-array binary search problem"},
    {"title": "Rotting Oranges", "slug": "rotting-oranges", "difficulty": "Medium", "reason": "classic multi-source BFS interview pattern"},
    {"title": "Best Time to Buy and Sell Stock", "slug": "best-time-to-buy-and-sell-stock", "difficulty": "Easy", "reason": "foundational greedy / prefix-min interview anchor"},
    {"title": "Container With Most Water", "slug": "container-with-most-water", "difficulty": "Medium", "reason": "canonical two-pointer interview problem"},
    {"title": "Jump Game", "slug": "jump-game", "difficulty": "Medium", "reason": "high-frequency greedy reachability pattern"},
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

GAP_FILL_CATEGORY = {
    "minimum-window-substring": "sliding_window",
    "daily-temperatures": "monotonic_stack",
    "serialize-and-deserialize-binary-tree": "trees_design",
    "largest-rectangle-in-histogram": "monotonic_stack",
    "edit-distance": "dynamic_programming",
    "task-scheduler": "greedy_counting",
    "kth-largest-element-in-an-array": "heaps_selection",
    "word-ladder": "graphs_bfs",
    "binary-tree-maximum-path-sum": "trees_dp",
    "find-median-from-data-stream": "heaps_design",
    "longest-increasing-subsequence": "dynamic_programming",
    "number-of-islands": "graphs_traversal",
    "course-schedule": "graphs_toposort",
    "top-k-frequent-elements": "heaps_hashing",
    "product-of-array-except-self": "arrays_prefix",
    "longest-consecutive-sequence": "arrays_hashing",
    "group-anagrams": "hashing_grouping",
    "find-minimum-in-rotated-sorted-array": "binary_search",
    "merge-intervals": "intervals",
    "coin-change": "dynamic_programming",
    "validate-binary-search-tree": "trees_invariants",
    "sliding-window-maximum": "sliding_window",
    "trapping-rain-water": "two_pointers_stack",
    "binary-tree-level-order-traversal": "trees_bfs",
    "lowest-common-ancestor-of-a-binary-tree": "trees_recursion",
    "subarray-sum-equals-k": "prefix_sum",
    "find-all-anagrams-in-a-string": "sliding_window",
    "search-in-rotated-sorted-array": "binary_search",
    "rotting-oranges": "graphs_bfs",
    "best-time-to-buy-and-sell-stock": "arrays_greedy",
    "container-with-most-water": "two_pointers",
    "jump-game": "greedy",
}

GAP_FILL_STAGE = {
    "minimum-window-substring": "advanced",
    "daily-temperatures": "foundation",
    "serialize-and-deserialize-binary-tree": "advanced",
    "largest-rectangle-in-histogram": "advanced",
    "edit-distance": "advanced",
    "task-scheduler": "foundation",
    "kth-largest-element-in-an-array": "foundation",
    "word-ladder": "advanced",
    "binary-tree-maximum-path-sum": "advanced",
    "find-median-from-data-stream": "advanced",
    "longest-increasing-subsequence": "advanced",
    "number-of-islands": "foundation",
    "course-schedule": "foundation",
    "top-k-frequent-elements": "foundation",
    "product-of-array-except-self": "foundation",
    "longest-consecutive-sequence": "foundation",
    "group-anagrams": "foundation",
    "find-minimum-in-rotated-sorted-array": "foundation",
    "merge-intervals": "foundation",
    "coin-change": "foundation",
    "validate-binary-search-tree": "foundation",
    "sliding-window-maximum": "advanced",
    "trapping-rain-water": "advanced",
    "binary-tree-level-order-traversal": "foundation",
    "lowest-common-ancestor-of-a-binary-tree": "foundation",
    "subarray-sum-equals-k": "foundation",
    "find-all-anagrams-in-a-string": "foundation",
    "search-in-rotated-sorted-array": "foundation",
    "rotting-oranges": "foundation",
    "best-time-to-buy-and-sell-stock": "foundation",
    "container-with-most-water": "foundation",
    "jump-game": "foundation",
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
    "validate binary search tree": (98, "validate-binary-search-tree"),
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
    "daily temperatures": (739, "daily-temperatures"),
}

PROBLEM_LOOKUP_BY_SLUG = {slug: (frontend_id, title) for title, (frontend_id, slug) in PROBLEM_LOOKUP.items()}


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
    if solved_count < 25:
        return {
            "review_core_multiplier": 1.15,
            "medium_gap_bonus": 1.45,
            "hard_gap_penalty": 4.1,
            "hard_anchor_threshold": 6.4,
            "foundation_bonus": 5.0,
            "advanced_bonus": -6.0,
        }
    if solved_count < 100:
        return {
            "review_core_multiplier": 1.08,
            "medium_gap_bonus": 1.0,
            "hard_gap_penalty": 2.1,
            "hard_anchor_threshold": 6.0,
            "foundation_bonus": 2.8,
            "advanced_bonus": -3.0,
        }
    if solved_count < 220:
        return {
            "review_core_multiplier": 1.04,
            "medium_gap_bonus": 0.35,
            "hard_gap_penalty": 0.45,
            "hard_anchor_threshold": 5.4,
            "foundation_bonus": 0.7,
            "advanced_bonus": 0.35,
        }
    return {
        "review_core_multiplier": 1.0,
        "medium_gap_bonus": 0.0,
        "hard_gap_penalty": 0.0,
        "hard_anchor_threshold": 5.4,
        "foundation_bonus": -0.6,
        "advanced_bonus": 1.6,
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


def collapse_submission_sessions(accepted_submissions: List[Dict[str, Any]]) -> List[int]:
    timestamps: List[int] = []
    for submission in accepted_submissions:
        try:
            ts = int(submission["timestamp"])
        except Exception:
            continue
        timestamps.append(ts)

    if not timestamps:
        return []

    timestamps.sort(reverse=True)
    session_timestamps: List[int] = [timestamps[0]]
    session_window_seconds = SOLVE_SESSION_WINDOW_MINUTES * 60

    for ts in timestamps[1:]:
        if session_timestamps[-1] - ts <= session_window_seconds:
            continue
        session_timestamps.append(ts)

    return session_timestamps


def recently_mentioned(title: str, history: List[Dict[str, Any]]) -> bool:
    return recent_mention_count(title, history) > 0


def recent_mention_count(title: str, history: List[Dict[str, Any]], lookback: int = 6) -> int:
    if not title:
        return 0
    needle = title.lower()
    count = 0
    for item in history[-lookback:]:
        for field in ["tldr", "why_now", "primary_action", "secondary_action", "stretch_action"]:
            if needle in str(item.get(field, "")).lower():
                count += 1
                break
    return count


def extract_plan_titles_from_memory(item: Dict[str, Any]) -> List[str]:
    titles: List[str] = []
    raw_tldr = str(item.get("tldr", ""))
    for raw_line in raw_tldr.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^\d+\.\s*", "", line)
        title = re.sub(r"^(Redo|Learn)\s+", "", line, flags=re.IGNORECASE).strip().rstrip(".")
        if title:
            titles.append(title)

    if len(titles) <= 1:
        for reason in item.get("problem_reasons", []) or []:
            match = re.match(r"^\s*(.+?)\s*:", str(reason).strip())
            if match:
                title = match.group(1).strip().rstrip(".")
                if title:
                    titles.append(title)

    deduped: List[str] = []
    seen = set()
    for title in titles:
        normalized = title.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(title)
    return deduped


def build_recent_gap_fill_context(
    history: List[Dict[str, Any]],
    gap_fill_catalog: List[Dict[str, Any]],
    lookback: int = 6,
) -> Dict[str, Counter]:
    title_to_item = {
        str(item.get("title", "")).strip().lower(): item
        for item in gap_fill_catalog
        if str(item.get("title", "")).strip()
    }
    title_counts: Counter = Counter()
    slug_counts: Counter = Counter()
    category_counts: Counter = Counter()

    for plan in history[-lookback:]:
        for title in extract_plan_titles_from_memory(plan):
            normalized = title.lower()
            item = title_to_item.get(normalized)
            if not item:
                continue
            slug = str(item.get("slug", "")).strip()
            category = GAP_FILL_CATEGORY.get(slug, "general")
            title_counts[normalized] += 1
            if slug:
                slug_counts[slug] += 1
            category_counts[category] += 1

    return {
        "title_counts": title_counts,
        "slug_counts": slug_counts,
        "category_counts": category_counts,
    }


def take_diverse_gap_fill_candidates(candidates: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    picked: List[Dict[str, Any]] = []
    category_counts: Counter = Counter()

    for candidate in candidates:
        category = candidate.get("category", "general")
        if category_counts[category] >= 2:
            continue
        picked.append(candidate)
        category_counts[category] += 1
        if len(picked) >= limit:
            return picked

    for candidate in candidates:
        if candidate in picked:
            continue
        picked.append(candidate)
        if len(picked) >= limit:
            break

    return picked


def build_learning_profile(
    snapshot: Dict[str, Any],
    history: List[Dict[str, Any]],
    config: Dict[str, Any],
    candidate_pools: Dict[str, Any],
) -> Dict[str, Any]:
    problems = snapshot.get("problems", [])
    ref_now = parse_snapshot_now(snapshot)
    solved_by_category: Dict[str, List[Dict[str, Any]]] = {}

    for problem in problems:
        slug = str(problem.get("slug", "")).strip()
        category = GAP_FILL_CATEGORY.get(slug)
        if not category:
            continue
        solved_by_category.setdefault(category, []).append(problem)

    category_summary = []
    for category in sorted({value for value in GAP_FILL_CATEGORY.values()}):
        solved_items = solved_by_category.get(category, [])
        sorted_items = sorted(
            solved_items,
            key=lambda item: (
                item.get("count", 1) or 1,
                age_hours_from_ts(item.get("last_ts"), ref_now),
            ),
        )
        category_summary.append({
            "category": category,
            "solved_count": len(solved_items),
            "sample_titles": [item.get("title") for item in sorted_items[:3]],
            "recent_recommendation_count": next(
                (
                    entry.get("recent_recommendation_count", 0)
                    for entry in candidate_pools.get("gap_fill_coverage_summary", [])
                    if entry.get("category") == category
                ),
                0,
            ),
        })

    undercovered_categories = [
        entry for entry in category_summary
        if entry["solved_count"] == 0
    ][:8]

    stale_or_fragile_solves = []
    for problem in problems:
        slug = str(problem.get("slug", "")).strip()
        count = problem.get("count", 1) or 1
        age_hours = age_hours_from_ts(problem.get("last_ts"), ref_now)
        category = GAP_FILL_CATEGORY.get(slug, "uncategorized")
        if count <= 2 or age_hours >= 24 * 30:
            stale_or_fragile_solves.append({
                "title": problem.get("title"),
                "slug": slug,
                "difficulty": problem.get("difficulty"),
                "count": count,
                "age_days": round(age_hours / 24.0, 1) if age_hours != float("inf") else None,
                "category": category,
            })

    stale_or_fragile_solves.sort(
        key=lambda item: (
            item["count"],
            -(item["age_days"] or 0),
            item["title"] or "",
        )
    )

    solved_titles = [problem.get("title") for problem in problems if problem.get("title")]
    recent_plan_titles = []
    for item in history[-6:]:
        recent_plan_titles.extend(extract_plan_titles_from_memory(item))

    return {
        "solved_count": len(problems),
        "difficulty_breakdown": summarize_snapshot(snapshot)["difficulty_breakdown"],
        "category_summary": category_summary,
        "undercovered_categories": undercovered_categories,
        "stale_or_fragile_solves": stale_or_fragile_solves[:20],
        "recent_plan_titles": recent_plan_titles[-24:],
        "solved_titles_sample": solved_titles[:120],
        "recommended_target_shape": get_target_shape(config, len(problems)),
    }


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
        accepted_sessions = collapse_submission_sessions(accepted)

        last_ts = None
        if accepted_sessions:
            try:
                last_ts = max(accepted_sessions)
            except Exception:
                last_ts = None

        return {
            "last_ts": last_ts,
            "count": len(accepted_sessions) if accepted_sessions else None,
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


def get_target_shape(config: Dict[str, Any], solved_count: int) -> Dict[str, int]:
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
    gap_fill_catalog = get_gap_fill_candidates_from_config(config)
    recent_gap_fill_context = build_recent_gap_fill_context(history, gap_fill_catalog)
    profile = solved_count_profile(len(problems))

    review_candidates = []
    fragile_candidates = []
    cooldown_excluded = []
    solved_gap_category_counts = Counter(
        GAP_FILL_CATEGORY.get(slug)
        for slug in solved_slugs
        if GAP_FILL_CATEGORY.get(slug)
    )

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
    for item in gap_fill_catalog:
        if item["slug"] in solved_slugs:
            continue

        title_key = item["title"].lower()
        title_repeat_count = recent_gap_fill_context["title_counts"].get(title_key, 0)
        category = GAP_FILL_CATEGORY.get(item["slug"], "general")
        category_repeat_count = recent_gap_fill_context["category_counts"].get(category, 0)
        interview_bonus = interview_core_bonus.get(item["slug"], 0.0)
        medium_stage_bonus = profile["medium_gap_bonus"] if item["difficulty"] == "Medium" else 0.0
        stage = GAP_FILL_STAGE.get(item["slug"], "foundation")
        stage_bonus = profile["foundation_bonus"] if stage == "foundation" else profile["advanced_bonus"]
        category_mastery_count = solved_gap_category_counts.get(category, 0)
        category_gap_bonus = max(0.0, 2.8 - min(category_mastery_count, 3) * 0.9)
        category_novelty_bonus = 1.1 if category_mastery_count == 0 else 0.0
        recent_title_penalty = title_repeat_count * 3.1
        recent_category_penalty = category_repeat_count * 1.45
        hard_stage_penalty = 0.0
        if item["difficulty"] == "Hard" and profile["hard_gap_penalty"] > 0:
            hard_stage_penalty = profile["hard_gap_penalty"]
            if interview_bonus >= profile["hard_anchor_threshold"]:
                hard_stage_penalty *= 0.35
        score = (
            difficulty_score(item["difficulty"]) * 1.35 +
            interview_bonus * 0.9 +
            medium_stage_bonus -
            stage_bonus +
            category_gap_bonus +
            category_novelty_bonus -
            hard_stage_penalty -
            recent_title_penalty -
            recent_category_penalty
        )

        gap_fill_candidates.append({
            "title": item["title"],
            "slug": item["slug"],
            "difficulty": item["difficulty"],
            "score": round(score, 2),
            "score_components": {
                "difficulty": round(difficulty_score(item["difficulty"]) * 1.35, 2),
                "interview_core_bonus": round(interview_bonus * 0.9, 2),
                "medium_stage_bonus": round(medium_stage_bonus, 2),
                "stage_bonus": round(stage_bonus, 2),
                "category_gap_bonus": round(category_gap_bonus, 2),
                "category_novelty_bonus": round(category_novelty_bonus, 2),
                "hard_stage_penalty": round(hard_stage_penalty, 2),
                "recent_title_penalty": round(recent_title_penalty, 2),
                "recent_category_penalty": round(recent_category_penalty, 2),
            },
            "why": item["reason"],
            "recently_mentioned": title_repeat_count > 0,
            "recent_mention_count": title_repeat_count,
            "recent_category_count": category_repeat_count,
            "category": category,
            "stage": stage,
            "category_mastery_count": category_mastery_count,
        })

    gap_fill_candidates.sort(key=lambda x: (-x["score"], x["title"]))
    gap_fill_candidates = take_diverse_gap_fill_candidates(gap_fill_candidates, 24)

    all_gap_categories = sorted({value for value in GAP_FILL_CATEGORY.values()})
    coverage_summary = []
    for category in all_gap_categories:
        coverage_summary.append({
            "category": category,
            "solved_count": solved_gap_category_counts.get(category, 0),
            "recent_recommendation_count": recent_gap_fill_context["category_counts"].get(category, 0),
        })

    return {
        "review_candidates": review_candidates[:16],
        "gap_fill_candidates": gap_fill_candidates[:24],
        "fragile_candidates": fragile_candidates[:6],
        "cooldown_excluded": cooldown_excluded[:12],
        "gap_fill_coverage_summary": coverage_summary[:12],
    }


def build_prompt(
    snapshot: Dict[str, Any],
    delta: Dict[str, Any],
    history: List[Dict[str, Any]],
    run_id: str,
    config: Dict[str, Any],
    target_shape: Dict[str, int],
    candidate_pools: Dict[str, Any],
    learning_profile: Dict[str, Any],
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
Python has prepared evidence for you:
- current solved-problem snapshot
- category coverage summary
- stale / fragile solve candidates
- recent recommendation memory
- a few optional candidate pools for review, gap fill, and fragile reinforcement

Your job is the smart part:
- decide what this user should repeat and what they should learn next
- use the evidence to choose the final plan
- follow the target shape exactly
- explain any unavoidable deviation clearly
- produce user-facing explanations, not planner-internal justifications

PLANNING BIAS:
Current mode is "{planning_bias}".

TARGET SHAPE FOR THIS RUN:
- Review problems: {target_shape["review"]}
- Gap-fill problems: {target_shape["gap_fill"]}
- Fragile reinforcement problems: {target_shape["fragile"]}

This target shape is the required output mix for the current planning mode.
Primary + Secondary + Stretch together must contain exactly this many review, gap-fill, and fragile reinforcement problems.

CORE PRINCIPLE:
Balanced does NOT mean equal representation.
Do NOT force symmetry across categories beyond the target shape.
Do not default to the same famous staple problems across different users when other candidates are comparably strong.
Favor undercovered categories and avoid repeating recently recommended titles or categories unless the user's snapshot gives a strong reason to do so.

CANDIDATE POOLS:
These are suggestions, not mandatory picks.

Review candidates:
{candidate_pools["review_candidates"]}

Gap-fill candidates:
{candidate_pools["gap_fill_candidates"]}

Gap-fill coverage summary:
{candidate_pools["gap_fill_coverage_summary"]}

Fragile candidates:
{candidate_pools["fragile_candidates"]}

Cooldown excluded:
{candidate_pools["cooldown_excluded"]}

RULES:
- Prefer the evidence above over generic interview folklore.
- You may choose outside the candidate pools if the snapshot and category evidence make that clearly better.
- Do NOT recommend anything in cooldown_excluded as a redo today.
- You must follow the target shape exactly unless there are not enough valid candidates for a required bucket. If you cannot follow it, explain the concrete blocking reason in the why_now summary.
- Fragile reinforcement is optional and should only be used if clearly valuable.
- Prefer the smallest strong session.
- Treat repeated recent recommendations as a real cost, not a tie-breaker afterthought.
- Never exceed {max_primary_review_problems} items in Primary.
- Total workload should usually stay around 4–5 problems.

TLDR RULE:
- TLDR must be direct instructions.
- It must list exact problems to do in order.
- Keep it concise.
- TLDR order must match Primary → Secondary → Stretch.
- TLDR must be a newline-separated string with exactly one problem per line.
- Each TLDR line must be numbered in order like:
  1. Merge Intervals
  2. Top K Frequent Elements
  3. Number of Islands
  4. Lowest Common Ancestor of a Binary Tree
- Do NOT write a prose sentence like "Do these 4 in order: A, B, C, D."
- Do NOT put multiple problems on one line.

NO ACTIVITY RULE:
If there is no new activity, keep the core recommendations stable.
Do not change problems just for variety.

IMPORTANT NOTES:
- Use "generated_at" as the current reference time for recency comparisons.
- Use timestamps and counts heavily.
- Treat old + low count as weak mastery.
- Use the category summary and missing-category evidence heavily.
- Output ONLY valid JSON.

LEARNING PROFILE:
Solved count:
{learning_profile["solved_count"]}

Difficulty breakdown:
{learning_profile["difficulty_breakdown"]}

Category coverage summary:
{learning_profile["category_summary"]}

Most undercovered categories:
{learning_profile["undercovered_categories"]}

Stale or fragile solves:
{learning_profile["stale_or_fragile_solves"]}

Recent plan titles:
{learning_profile["recent_plan_titles"]}

Solved titles sample:
{learning_profile["solved_titles_sample"]}

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
  "tldr": "1. Merge Intervals\n2. Top K Frequent Elements\n3. Number of Islands\n4. Lowest Common Ancestor of a Binary Tree",
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


def enrich_plan_with_problem_metadata(
    plan_json: Dict[str, Any],
    snapshot: Dict[str, Any],
    candidate_pools: Dict[str, Any] | None = None,
) -> None:
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

    candidate_title_to_slug: Dict[str, str] = {}
    for pool_name in ("review_candidates", "gap_fill_candidates", "fragile_candidates"):
        for item in ((candidate_pools or {}).get(pool_name) or []):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            slug = str(item.get("slug", "")).strip()
            if title and slug:
                candidate_title_to_slug[title.lower()] = slug

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

        if not problem:
            candidate_slug = candidate_title_to_slug.get(title_lower)
            if candidate_slug:
                lookup_data = PROBLEM_LOOKUP_BY_SLUG.get(candidate_slug)
                if lookup_data:
                    frontend_id, _ = lookup_data
                    problem_metadata[title] = {
                        "frontend_id": frontend_id,
                        "slug": candidate_slug,
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
    target_shape = get_target_shape(config, len(snapshot.get("problems", [])))
    candidate_pools = build_candidate_pools(snapshot, history_plans, config)
    learning_profile = build_learning_profile(snapshot, history_plans, config, candidate_pools)

    save_json(snapshot_path, snapshot)
    save_json(candidate_buckets_path, {
        "planning_bias": config.get("planning_bias", "balanced_growth"),
        "target_shape": target_shape,
        "candidate_pools": candidate_pools,
        "learning_profile": learning_profile,
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
        learning_profile=learning_profile,
    )

    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    emit_progress(5, 6, "Generating final recommendation with GPT")
    plan_json = call_openai_for_plan(prompt)
    plan_json["timezone"] = resolve_timezone_name(config)
    plan_json["date"] = now.date().isoformat()
    
    # Enrich plan with problem metadata (frontend_id, slug)
    enrich_plan_with_problem_metadata(plan_json, snapshot, candidate_pools)

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
