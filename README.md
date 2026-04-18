# LeetLoop

LeetLoop is a local LeetCode practice planner that uses your actual solve history to recommend what to work on next.

It pulls your solved problems from LeetCode, tracks timestamps and solve counts over time, and generates a small, focused daily plan. The goal is simple: spend your time on the highest-impact problems instead of guessing what to practice.

The system uses a hybrid approach:

- Python handles deterministic logic such as cooldown windows, planning bias, and candidate selection
- GPT handles prioritization, tradeoffs, and the final recommendation

---

## Requirements

- Python 3.10+
- OpenAI API key
- LeetCode session cookies:
  - `LEETCODE_SESSION`
  - `LEETCODE_CSRFTOKEN`

## Notes

- Local-first app
- Browser-based UI
- Source install is currently the recommended path
- macOS/Linux setup is terminal-based and currently best suited to technical users

---

## What it does

- Fetches solved problem history from LeetCode
- Tracks when you last solved each problem and how many times
- Detects changes between runs
- Preserves recommendation history across runs through the local `history/` folder
- Applies a cooldown so problems you just solved are not immediately recommended again
- Supports different planning styles depending on your goal
- Outputs both a readable plan and structured data for debugging

---

## Recommended usage

The recommended way to use LeetLoop is as a small local app.

The app:

- shows your latest recommendation in a browser
- lets you trigger a run manually with a button
- keeps a daily run time in local config
- runs the planner on a built-in schedule without relying on a hidden OS task
- keeps all state, credentials, and recommendation history on your own machine

This is simpler and less opaque than relying on a background scheduled script alone.

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

## Configuration

Planner configuration lives in:

```
config/config.json
```

App configuration lives in:

```
config/app_config.json
```

`config/config.json` controls planning behavior such as planning bias and candidate tuning.

`config/app_config.json` controls local app behavior such as:

- host
- port
- daily run time
- whether the browser should open when the app starts

### Planning modes

- `balanced_growth`
  Mix of review and new problems (typically 2 and 2)

- `interview_maintenance`
  Heavier on review (typically 3 review, 1 new)

- `aggressive_gap_fill`
  Focus on new patterns (typically 1 review, 3 new)

---

## Project structure

```text
LeetLoop/
|-- src/
|   |-- run_pipeline.py         # Core planner logic
|   |-- run_service.py          # Web UI server and background agent
|   `-- app_launcher.py         # Entry point for bundled executable
|-- build_scripts/
|   |-- build.py                # PyInstaller build script
|   `-- README.md               # Build instructions
|-- config/
|   |-- config.json             # Planner configuration
|   `-- app_config.json         # Local app defaults
|-- examples/
|   |-- sample_snapshot.json
|   |-- sample_recommendation.json
|   |-- sample_candidate_buckets.json
|   `-- sample_plan_memory.json
|-- history/                    # Local run output (gitignored)
|-- setup_windows.bat           # Windows setup (source install)
|-- setup.sh                    # macOS/Linux setup (source install)
|-- run_app.bat                 # Windows app launcher
|-- run_app.sh                  # macOS/Linux app launcher
|-- requirements.txt            # Runtime dependencies
|-- requirements-build.txt      # Build-only dependencies
|-- .env.example
|-- .gitattributes
`-- README.md
```

---

## Setup

### Recommended: Run From Source

Source install is the primary supported path right now.

#### Windows

1. Clone the repository.
2. Run `setup_windows.bat`:

```bat
setup_windows.bat
```

This will:
- require Python 3.10+
- create a local virtual environment
- install Python dependencies
- create `.env` from `.env.example`
- prompt for `OPENAI_API_KEY`
- prompt for `LEETCODE_SESSION`
- prompt for `LEETCODE_CSRFTOKEN`

3. Start the app:

```bat
run_app.bat
```

Optional quick validation before launch:

```bat
.venv\Scripts\python.exe src\run_service.py --check-setup
```

#### macOS / Linux

1. Clone the repository.
2. Open a terminal in the repo and run:

```bash
chmod +x setup.sh
./setup.sh
```

This will:
- require Python 3.10+
- create a local virtual environment
- install Python dependencies
- create `.env` from `.env.example`
- prompt for `OPENAI_API_KEY`
- prompt for `LEETCODE_SESSION`
- prompt for `LEETCODE_CSRFTOKEN`

3. Start the app:

```bash
chmod +x run_app.sh
./run_app.sh
```

Optional quick validation before launch:

```bash
.venv/bin/python src/run_service.py --check-setup
```

### Optional Packaged Launcher

The packaged launcher exists as a secondary path, but source install is still the documented default until the packaged flow is fully proven across platforms.

### Manual Setup (Advanced)

1. Copy `.env.example` to `.env`.
2. Fill in:
- `OPENAI_API_KEY`
- `LEETCODE_SESSION`
- `LEETCODE_CSRFTOKEN`

3. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

4. Start the app:

```bash
python src/run_service.py --ui
```

Optional quick validation:

```bash
python src/run_service.py --check-setup
```

Or run the planner directly once:

```bash
python src/run_pipeline.py
```

### Building Your Own Executable

Standalone executable builds are a developer workflow, not the primary setup path.

1. Install build dependencies:

```bash
pip install -r requirements-build.txt
```

2. Build the executable:

```bash
python build_scripts/build.py
```

The executable will be created in `dist/`.

---

## Required environment variables

`.env.example` contains the required keys:

```dotenv
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4
LEETCODE_SESSION=...
LEETCODE_CSRFTOKEN=...
```

Notes:

- `OPENAI_API_KEY` is required for plan generation
- `LEETCODE_SESSION` and `LEETCODE_CSRFTOKEN` are required for authenticated LeetCode GraphQL access
- `.env` is local-only and must never be committed

---

## Running LeetLoop

### Recommended app mode

On Windows:

```bat
run_app.bat
```

On macOS / Linux:

```bash
./run_app.sh
```

This starts the local web app and embedded scheduler.

### First-run commands

- Windows: `setup_windows.bat` then `run_app.bat`
- macOS/Linux: `./setup.sh` then `./run_app.sh`

### Quick setup check

Run this before launching the app if you want a fast validation pass:

On Windows:

```bat
.venv\Scripts\python.exe src\run_service.py --check-setup
```

On macOS / Linux:

```bash
.venv/bin/python src/run_service.py --check-setup
```

It checks:

- Python version
- `.env` presence
- required credentials
- config JSON loading

### Direct Python entrypoints

Run the app directly:

```bash
python src/run_service.py --ui
```

Run the planner once without the UI:

```bash
python src/run_pipeline.py
```

## Daily automation

LeetLoop now supports daily local automation through the built-in app scheduler.

Why this is the recommended model:

- `history/` persists naturally across runs
- your credentials stay local in `.env`
- your daily recommendation output remains private
- the schedule is visible inside the app rather than hidden in the OS
- the same app can both display the latest plan and trigger new runs

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
- score components for ranked candidates

---

## Design principles

- Keep sessions small and realistic
- Avoid redoing problems too soon
- Treat old, low-count problems as weak mastery
- Config controls structure
- GPT handles prioritization
- Keep private user data local by default

---

## Security notes

- `.env` is ignored by Git
- `history/` is ignored by Git
- example files are safe to publish
- do not commit real cookies or API keys

---

## Roadmap

- private phone notifications
- richer local dashboard
- better canonical problem detection
- pattern tracking
- easier cross-platform app packaging

---

## Contributing

Feel free to fork and experiment. The project is designed to be simple and easy to modify.

---

## License

MIT License
