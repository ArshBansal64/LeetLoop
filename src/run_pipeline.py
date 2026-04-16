from dotenv import load_dotenv

import json
import os
import datetime
import webbrowser
import requests
import time
from typing import Any, Dict, List, Tuple

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=ENV_PATH)

HISTORY_DIR = os.path.join(PROJECT_ROOT, "history")
os.makedirs(HISTORY_DIR, exist_ok=True)

GRAPHQL_URL = "https://leetcode.com/graphql"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

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
]

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


def now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def iso_utc(dt: datetime.datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def format_local_readable(dt_str: str) -> str:
    if not dt_str:
        return "Unknown"
    try:
        dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        local_dt = dt.astimezone()
        return local_dt.strftime("%b %d, %Y %I:%M:%S %p %Z")
    except Exception:
        return dt_str


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


def difficulty_score(difficulty: str) -> float:
    return {"Easy": 1.0, "Medium": 2.0, "Hard": 3.0}.get(difficulty, 1.0)


def get_gap_fill_candidates_from_config(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    configured = config.get("canonical_gap_candidates")
    if isinstance(configured, list) and configured:
        normalized = []
        for item in configured:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            slug = str(item.get("slug", "")).strip()
            if not title or not slug:
                continue
            normalized.append({
                "title": title,
                "slug": slug,
                "difficulty": str(item.get("difficulty", "Medium")).strip() or "Medium",
                "reason": str(item.get("reason", "canonical interview anchor")).strip() or "canonical interview anchor",
            })
        if normalized:
            return normalized
    return DEFAULT_GAP_FILL_CANDIDATES


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
        priority_bonus = review_priority_bonus.get(slug, canonical_bonus)
        deprioritized_penalty = 4.5 if slug in review_deprioritized_slugs else 0.0
        generic_easy_penalty = 4.0 if is_generic_easy_review(difficulty, priority_bonus) else 0.0
        low_transfer_easy_penalty = 2.5 if is_low_transfer_easy(slug, difficulty, canonical_bonus) else 0.0
        obscure_penalty = 2.0 if is_obscure_or_contesty(slug, title, canonical_bonus) else 0.0
        recent_plan_penalty = 1.0 if recently_mentioned(title, history) else 0.0
        age_component = min(age_hours / 24.0, 365.0) * 0.03
        low_count_component = max(0, 3 - min(count, 3)) * 2.0
        difficulty_component = difficulty_score(difficulty) * 1.2
        review_score = (
            age_component +
            low_count_component +
            difficulty_component +
            priority_bonus -
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
        score = difficulty_score(item["difficulty"]) * 2.0 - recent_penalty

        gap_fill_candidates.append({
            "title": item["title"],
            "slug": item["slug"],
            "difficulty": item["difficulty"],
            "score": round(score, 2),
            "score_components": {
                "difficulty": round(difficulty_score(item["difficulty"]) * 2.0, 2),
                "recent_plan_penalty": recent_penalty,
            },
            "why": item["reason"],
            "recently_mentioned": recently_mentioned(item["title"], history),
        })

    gap_fill_candidates.sort(key=lambda x: (-x["score"], x["title"]))

    return {
        "review_candidates": review_candidates[:8],
        "gap_fill_candidates": gap_fill_candidates[:10],
        "fragile_candidates": fragile_candidates[:5],
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

NO ACTIVITY RULE:
If there is no new activity, keep the core recommendations stable.
Do not change problems just for variety.

IMPORTANT NOTES:
- Use "generated_at" as the current reference time for recency comparisons.
- Use timestamps and counts heavily.
- Treat old + low count as weak mastery.
- Output ONLY valid JSON.

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
  "date": "{datetime.date.today().isoformat()}",
  "tldr": "...",
  "why_now": "...",
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
        raise RuntimeError(f"OpenAI API error. status={resp.status_code}, payload={data}")

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
        "why_now",
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

    return parsed


def make_readable_plan_text(plan_json: Dict[str, Any]) -> str:
    do_not_focus = plan_json.get("do_not_focus_on", [])
    insights = plan_json.get("insights", [])

    generated_at_utc = plan_json.get("generated_at")
    generated_at_local = format_local_readable(generated_at_utc)

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
{plan_json.get("why_now")}

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
    verify_env_setup()
    verify_leetcode_auth()

    config = load_config()
    existing_run_dirs = get_existing_run_dirs()
    prev_snapshot = {}

    if existing_run_dirs:
        latest_run = existing_run_dirs[-1]
        prev_snapshot_path = os.path.join(HISTORY_DIR, latest_run, "snapshot.json")
        prev_snapshot = load_json(prev_snapshot_path, {})

    now = now_utc()
    run_id = now.strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(HISTORY_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    snapshot_path = os.path.join(run_dir, "snapshot.json")
    prompt_path = os.path.join(run_dir, "prompt.txt")
    recommendation_path = os.path.join(run_dir, "recommendation.json")
    readable_plan_path = os.path.join(run_dir, "recommendation.txt")
    plan_memory_path = os.path.join(run_dir, "plan_memory.json")
    candidate_buckets_path = os.path.join(run_dir, "candidate_buckets.json")

    snapshot = generate_real_snapshot(prev_snapshot=prev_snapshot)
    delta = diff(prev_snapshot, snapshot)

    print("Snapshot problem_count:", snapshot.get("problem_count"))
    if snapshot.get("problems"):
        print("Min frontend_id:", snapshot["problems"][0].get("frontend_id"))
        print("Max frontend_id:", snapshot["problems"][-1].get("frontend_id"))

    history_plans = get_recent_plan_memory()
    target_shape = get_target_shape(config)
    candidate_pools = build_candidate_pools(snapshot, history_plans, config)

    save_json(snapshot_path, snapshot)
    save_json(candidate_buckets_path, {
        "planning_bias": config.get("planning_bias", "balanced_growth"),
        "target_shape": target_shape,
        "candidate_pools": candidate_pools,
    })

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

    plan_json = call_openai_for_plan(prompt)

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

    webbrowser.open(f"file://{os.path.abspath(readable_plan_path)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print()
        print("Pipeline failed.")
        print(str(e))
