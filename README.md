# LeetLoop

LeetLoop is a local LeetCode practice planner that uses your actual solve history to recommend what to work on next.

It pulls your solved problems from LeetCode, tracks timestamps and solve counts over time, and generates a small, focused daily plan. The goal is simple: spend your time on the highest-impact problems instead of guessing what to practice.

The system uses a hybrid approach:

- Python handles deterministic logic such as cooldown windows, planning bias, and candidate selection
- GPT handles prioritization, tradeoffs, and the final recommendation

---

## What it does

- Fetches solved problem history from LeetCode
- Tracks when you last solved each problem and how many times
- Detects changes between runs (what you’ve recently worked on)
- Applies a cooldown so problems you just solved are not immediately recommended again
- Supports different planning styles depending on your goal
- Outputs both a readable plan and structured data for debugging

---

## How it works

Each run follows the same flow:

1. Pull your solved problems from LeetCode
2. Build a snapshot of your current state (timestamps, counts, difficulty)
3. Compare it with the previous run to detect activity
4. Generate candidate pools:
   - review (old, low-count problems)
   - gap fill (important unsolved problems)
   - fragile (recent but not yet stable)
5. Apply config rules (like session size and bias)
6. Let GPT choose the final plan and explain why

---

## Example output

```
🔥 Daily LeetCode Plan

Generated (Local): Apr 16, 2026 01:12:39 AM Pacific Daylight Time
Generated (UTC): 2026-04-16T08:12:39.544787Z
Run ID: 2026-04-16_08-11-43

━━━━━━━━━━━━━━━━━━━━

TLDR (DO THIS):
1. Redo Median of Two Sorted Arrays.
2. Redo Find Elements in a Contaminated Binary Tree.
3. Learn Edit Distance.
4. Learn Serialize and Deserialize Binary Tree.
```

---

## Configuration

Configuration lives in:

```
config/planner_config.json
```

Example:

```json
{
  "planning_bias": "balanced_growth",
  "history_days": 7,
  "max_primary_review_problems": 4
}
```

### Planning modes

- `balanced_growth`  
  Mix of review and new problems (typically 2 and 2)

- `interview_maintenance`  
  Heavier on review (typically 3 review, 1 new)

- `aggressive_gap_fill`  
  Focus on new patterns (typically 1 review, 3 new)

---

## Project structure

```
LeetLoop/
│
├── src/
│   └── run_pipeline.py
│
├── config/
│   └── planner_config.json
│
├── examples/
│   ├── sample_snapshot.json
│   ├── sample_plan.json
│   └── sample_candidate_buckets.json
│
├── history/
│
├── setup.bat                 # Windows setup script
├── run_now.bat               # run the planner immediately
├── schedule_daily.bat        # create/update daily scheduled task
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## Output

Each run creates a new folder:

```
history/<run_id>/
```

With:

- `snapshot.json`
- `prompt.txt`
- `recommendation.json`
- `recommendation.txt`
- `plan_memory.json`
- `candidate_buckets.json`

---

## Setup

### Recommended Windows setup

1. Run:

```bat
setup.bat
```

This will:

- create a local virtual environment
- install Python dependencies
- create `.env` from `.env.example` if it does not already exist

2. Open `.env` and fill in your credentials.

3. Run the planner once:

```bat
run_now.bat
```

4. Optionally schedule it daily:

```bat
schedule_daily.bat
```

By default, this creates a Windows Task Scheduler job for 08:00.

To choose a different time:

```bat
schedule_daily.bat 07:30
```

---

### Manual setup

If you do not want to use the batch scripts:

1. Create a local `.env` file based on `.env.example`
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) Update `config/planner_config.json`
4. Run:

```bash
python src/run_pipeline.py
```

---

## Running the planner

### Recommended

```bat
run_now.bat
```

### Direct Python entrypoint

```bash
python src/run_pipeline.py
```

---

## Daily automation

For private personal usage, the recommended deployment model is local scheduled execution.

Why:

- `history/` persists naturally across runs
- your credentials stay local in `.env`
- your daily recommendation output remains private
- setup is simpler than splitting execution across public and private repositories

On Windows, `schedule_daily.bat` uses Task Scheduler to run `run_now.bat` daily.

---

## Security notes

- `.env` is ignored by Git
- `history/` is ignored by Git
- Example files are safe to publish
- Do not commit real cookies or API keys

---

## Debugging

If something looks off, start with:

```
candidate_buckets.json
```

It shows:

- planning mode
- target shape
- candidate pools
- cooldown exclusions

---

## Design principles

- Keep sessions small and realistic
- Avoid redoing problems too soon
- Treat old, low-count problems as weak mastery
- Config controls structure
- GPT handles prioritization

---

## Roadmap

- GitHub Actions automation
- Simple UI / dashboard
- LeetHub integration
- Better canonical problem detection
- Pattern tracking

---

## Contributing

Feel free to fork and experiment. The project is designed to be simple and easy to modify.

---

## License

MIT License
