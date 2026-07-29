# flake-wrangler

> Detect and quarantine flaky tests by running suites repeatedly to surface non-deterministic pass/fail behavior.

## Project overview

**flake-wrangler** is a command-line tool that hunts down *flaky tests* — tests
that pass and fail non-deterministically without any change to the code under
test. It runs your test suite (or a targeted subset) multiple times, records the
pass/fail outcome of each individual test across runs, and reports which tests
are unstable. Optionally, it can emit a quarantine list so CI can skip or
soft-fail known-flaky tests until they're fixed.

## Motivation

Flaky tests are one of the most corrosive problems in a CI pipeline:

- They erode trust in the test suite ("just re-run it, it's probably flaky").
- They mask real regressions behind noise.
- They waste engineering time on spurious failures and manual re-runs.

The hard part is *identifying* flakes reliably — a single failure doesn't prove
flakiness, and a single pass doesn't prove stability. flake-wrangler makes the
statistical case for you by running tests N times and measuring the failure
rate per test, turning "I think that test is flaky" into "this test failed 4/20
runs."

## Use cases

- **CI maintainers** who want a scheduled job that flags newly-flaky tests before
  they poison the main branch.
- **Developers** debugging a specific intermittently-failing test locally.
- **Release engineers** who need a quarantine list to keep the pipeline green
  while flakes are triaged.
- **Teams adopting a test suite** who want a flakiness baseline for a codebase.

## How to use

Quickstart:

```bash
# Install (planned distribution)
pip install flake-wrangler        # or: pipx install flake-wrangler

# Run the whole suite 20 times and report flakiness
flake-wrangler run --runner pytest --repeat 20

# Target a subset and set a flakiness threshold
flake-wrangler run --runner pytest --repeat 30 --threshold 0.1 -- tests/integration

# Emit a quarantine file for tests failing >10% of runs
flake-wrangler run --repeat 20 --threshold 0.1 --quarantine-out quarantine.txt

# Choose report format and write to a file
flake-wrangler run --repeat 25 --report md --out flakes.md
flake-wrangler run --repeat 25 --report json --out flakes.json
```

Optional config defaults via `flake-wrangler.toml`:

```toml
[run]
runner = "pytest"
repeat = 20
threshold = 0.1
report = "md"
out = "flakes.md"
quarantine-out = "quarantine.txt"
```

Any explicit CLI flag overrides config values.

### Exit codes

`flake-wrangler run` returns:

- `0` when no flaky tests are detected.
- `1` when flaky tests are detected and fail-on-flaky mode is enabled.
- `2` for argument/config usage errors (from `argparse`).

Fail-on-flaky mode is configurable:

- `--fail-on-flaky` (default behavior)
- `--no-fail-on-flaky`
- `run.fail-on-flaky = true/false` in `flake-wrangler.toml`

## Example commands or workflows

Detect flakes and produce a JSON report:

```bash
flake-wrangler run --runner pytest --repeat 25 --report json --out flakes.json
```

Example report (illustrative):

```
Test                                  Runs  Fails  Failure rate  Verdict
tests/test_api.py::test_timeout         25      6         0.24   FLAKY
tests/test_db.py::test_migrate          25      0         0.00   stable
tests/test_auth.py::test_token_refresh  25      1         0.04   suspect
```

JSON schema (`--report json`):

```json
{
  "schema_version": "1.0",
  "tool": "flake-wrangler",
  "threshold": 0.1,
  "repeat": 20,
  "tests": [
    {
      "test": "tests/test_api.py::test_timeout",
      "runs": 20,
      "fails": 4,
      "failure_rate": 0.2,
      "verdict": "flaky"
    }
  ],
  "never_ran": ["tests/test_slow.py::test_only_skipped"]
}
```

- `tests` contains one object per executed test.
- `never_ran` contains tests observed only as skipped across all runs.

Wire it into CI as a nightly job:

```yaml
# .github/workflows/flake-scan.yml
name: flake scan

on:
  schedule:
    - cron: "0 3 * * *"
  workflow_dispatch:

jobs:
  flake-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install flake-wrangler
        run: |
          python -m pip install --upgrade pip
          pip install -e .
      - name: Detect flaky tests
        run: |
          flake-wrangler run \
            --runner pytest \
            --repeat 20 \
            --threshold 0.1 \
            --report md \
            --out flakes.md \
            --quarantine-out quarantine.txt \
            --fail-on-flaky \
            -- pytest -q
      - name: Upload flake report artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: flake-wrangler-report
          path: |
            flakes.md
            quarantine.txt
```

## Current status / next milestones

- [x] Repository bootstrapped with README + PLAN
- [x] Core run loop: execute a runner N times and capture per-test results (#1)
- [x] pytest results adapter (parse per-test outcomes) (#2)
- [x] Flakiness classification + threshold logic (#3)
- [x] Report formats: table / JSON / Markdown (#4)
- [x] Quarantine list output (#5)
- [x] CLI argument parsing and config file (#6)
- [x] CI-friendly exit codes and GitHub Actions example (#7)

See the [issue backlog](https://github.com/rwrife/flake-wrangler/issues) and
[PLAN.md](./PLAN.md) for details.
