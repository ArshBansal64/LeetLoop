# LeetLoop

LeetLoop is a local Python tool that turns your real LeetCode history into a small, high-value daily interview practice plan.

It uses a hybrid planner design:

- Python handles deterministic control like planning shape, cooldown filtering, and candidate generation.
- GPT chooses the final plan from those candidate pools and writes the final recommendation.

You can run it locally or wire it into GitHub Actions for a daily practice loop.

## Goals

- Generate a small, high-value daily LeetCode plan for interview readiness.
- Keep the planner hybrid, with Python enforcing planning shape, cooldown, and candidate generation, and GPT choosing the final plan from those candidate pools.
- Preserve run-to-run stability when there is no new activity.
- Keep outputs debuggable through saved artifacts.

## How it works

Each run:

1. Pulls your solved-problem history from LeetCode.
2. Builds a fresh snapshot with timestamps and solve counts.
3. Diffs against previous runs to detect new activity.
4. Generates review, gap-fill, fragile, and cooldown candidate buckets in Python.
5. Sends the snapshot summary and candidate pools to GPT.
6. Writes both machine-readable and human-readable output files.

## Project structure

- `src/run_pipeline.py` - main pipeline
- `config/config.json` - non-secret planner config
- `examples/` - safe sample outputs
- `history/` - local run outputs only, gitignored
- `.env.example` - template for local secrets

## Setup

1. Create a local `.env` file based on `.env.example`.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Update `config/config.json` if you want to tune planning behavior.

Optional:

- Run it locally by hand.
- Or schedule it with GitHub Actions or another cron-style runner.

## Required environment variables

`.env.example` contains the required keys:

```dotenv
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4
LEETCODE_SESSION=...
LEETCODE_CSRFTOKEN=...
```

Notes:

- `OPENAI_API_KEY` is required for plan generation.
- `LEETCODE_SESSION` and `LEETCODE_CSRFTOKEN` are required for authenticated LeetCode GraphQL access.
- `.env` is local-only and must never be committed.

## Running the planner

```bash
python src/run_pipeline.py
```

Each run writes a timestamped folder under `history/` containing:

- `snapshot.json`
- `candidate_buckets.json`
- `prompt.txt`
- `recommendation.json`
- `recommendation.txt`
- `plan_memory.json`

The most useful debug artifact is `candidate_buckets.json`, because it shows:

- the active planning bias
- the target review/gap shape
- ranked review candidates
- ranked gap-fill candidates
- fragile candidates
- cooldown exclusions
- score components for the ranked candidates

## Config behavior

`config/config.json` controls planning shape and curated candidate lists.

Current supported planning biases:

- `balanced_growth` -> `2 review + 2 gap_fill`
- `interview_maintenance` -> `3 review + 1 gap_fill`
- `aggressive_gap_fill` -> `1 review + 3 gap_fill`

Fragile reinforcement is optional and is not part of the default required shape.

It also lets you tune:

- curated canonical gap-fill candidates
- review-priority bonuses for canonical solved problems
- review deprioritization for noisy solved problems

## Repo name

Recommended repository name: `LeetLoop`
