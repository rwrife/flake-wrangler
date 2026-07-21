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

> Status: early scaffold. The CLI described here is the target interface; see
> the issue backlog and PLAN.md for what's implemented vs. planned.

Quickstart:

```bash
# Install (planned distribution)
pip install flake-wrangler        # or: pipx install flake-wrangler

# Run the whole suite 20 times and report flakiness
flake-wrangler run --runner pytest --repeat 20

# Target a subset and set a flakiness threshold
flake-wrangler run --runner pytest -- tests/integration --repeat 30 --threshold 0.1

# Emit a quarantine file for tests failing >10% of runs
flake-wrangler run --repeat 20 --threshold 0.1 --quarantine-out quarantine.txt
```

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

Wire it into CI as a nightly job:

```yaml
# .github/workflows/flake-scan.yml (planned)
on:
  schedule:
    - cron: "0 3 * * *"
jobs:
  flake-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install flake-wrangler
      - run: flake-wrangler run --runner pytest --repeat 20 --report md --out flakes.md
```

## Current status / next milestones

- [x] Repository bootstrapped with README + PLAN
- [ ] Core run loop: execute a runner N times and capture per-test results (#1)
- [ ] pytest results adapter (parse per-test outcomes) (#2)
- [ ] Flakiness classification + threshold logic (#3)
- [ ] Report formats: table / JSON / Markdown (#4)
- [ ] Quarantine list output (#5)
- [ ] CLI argument parsing and config file (#6)
- [ ] CI-friendly exit codes and GitHub Actions example (#7)

See the [issue backlog](https://github.com/rwrife/flake-wrangler/issues) and
[PLAN.md](./PLAN.md) for details.
