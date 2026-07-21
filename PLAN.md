# flake-wrangler — Plan

## Scope

A small, focused CLI that detects flaky tests by repeated execution and reports
per-test failure rates. In scope:

- Running an arbitrary test command / runner N times.
- Parsing per-test pass/fail outcomes (starting with pytest).
- Classifying tests as stable / suspect / flaky against a threshold.
- Emitting human-readable and machine-readable reports.
- Producing a quarantine list of known-flaky tests.
- CI-friendly exit codes.

## Tech approach

- **Language:** Python 3.11+ (broad availability, strong pytest ecosystem).
- **Structure:** single package `flake_wrangler` with a `cli` entrypoint,
  a `runner` abstraction, per-runner `adapters`, a `classifier`, and
  `reporters`.
- **Runner abstraction:** invoke the test command via subprocess, capturing
  structured output where possible (e.g. pytest's `--junit-xml` or
  `--report-log`) to get reliable per-test results rather than scraping stdout.
- **Classification:** failure_rate = fails / runs; verdict from thresholds
  (0 = stable, >0 and <threshold = suspect, >=threshold = flaky).
- **Reporters:** pluggable table / json / md formatters sharing one result model.
- **Config:** CLI flags first; optional `flake-wrangler.toml` for defaults.
- **Testing:** unit tests with a fake runner adapter feeding synthetic results;
  no dependency on a real flaky suite for CI determinism.

## Milestones

1. **M1 — Core loop:** run a command N times, aggregate raw pass/fail per test.
2. **M2 — pytest adapter:** parse JUnit XML / report-log into a normalized model.
3. **M3 — Classification & reporting:** thresholds + table/JSON/MD output.
4. **M4 — Quarantine & CI:** quarantine file output, exit codes, Actions example.
5. **M5 — Polish:** config file, docs, packaging for pip/pipx.

## Non-goals

- Automatically *fixing* flaky tests (only detection + reporting).
- Deep language coverage beyond pytest initially (adapters can be added later).
- A hosted service / dashboard — this is a local + CI CLI tool.
- Root-causing flakiness (timing, ordering, external deps) beyond surfacing it.
