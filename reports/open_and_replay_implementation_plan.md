# Open Snapshot And Replay Implementation Plan

## Objective

Close the main remaining gaps in the prediction-market deliverable by:

1. bringing the `open` snapshot up to the same standard as `mid` and `24h`
2. upgrading replay from a log-summary tool into a latency-aware feasibility simulator
3. closing remaining assignment-compliance gaps in the Makefile and reporting flow

## Workstream 1: Complete `open`

### Goal

Make `open` a real, tested, leakage-safe prediction timestamp alongside `mid` and `24h`.

### Required Behavior

- `open` means the first available price within 60 minutes of market creation
- if no valid price exists in that window, the market should be excluded from the `open` snapshot dataset
- all features used at `open` must be restricted to information available on or before the `open` timestamp

### Planned Work

1. Confirm the raw ingestion fields that represent:
   - market creation time
   - first available price timestamp
   - price history timestamp granularity
2. Add or finish `open` snapshot extraction in `src/features`
3. Produce an `open` feature dataset parallel to existing `mid` and `24h` datasets
4. Reuse leakage checks already implemented in `src/features/leakage_checks.py`
5. Extend offline evaluation so `open`, `mid`, and `24h` are produced from the same reporting path
6. Update final reports and artifacts so `open` no longer appears as zero usable rows

### Tests To Add Or Tighten

- valid first price selected within the 60-minute window
- market rejected if only later prices exist
- exact 60-minute boundary behavior
- no post-resolution columns at `open`
- `open` snapshot occurs after market creation and before close

### Definition Of Done

- `open` dataset builds successfully
- `open` evaluation runs end-to-end
- `open` appears in the offline summary with real row counts and Brier results
- unit tests prove timestamp correctness and leakage safety

## Workstream 2: Upgrade Replay To Latency-Aware Feasibility

### Goal

Satisfy Mario's stronger replay requirement:

> recompute detection and estimate feasibility under latency assumptions

### Current State

The current replay tool summarizes scanner logs and produces a markdown report, but it does not:

- recompute detector logic from stored inputs
- rerun the detector at `t + latency`
- estimate false positives from edge decay

### Minimum Viable Replay Simulator

Replay should:

1. load logged flags and associated scanner state
2. reconstruct the detection inputs used at the original flag time
3. locate the nearest later snapshot for each configured latency tier
4. recompute executable pricing, fees, and net edge at `t + latency`
5. classify each flag as:
   - still positive
   - degraded but positive
   - false positive (`net_edge <= 0`)

### Initial Latency Tiers

- `250ms`
- `1s`
- `3s`

If prediction-market logging resolution is coarser than those intervals, replay should document the effective nearest available timestamp used.

### Planned Work

1. Enrich logged scanner events so replay has enough input state to recompute detection
2. Add replay functions in `src/backtest` for:
   - loading flag events
   - reconstructing detector inputs
   - rerunning executable pricing and edge computation
   - comparing original edge versus replay edge
3. Produce summary outputs for:
   - total opportunities
   - average net-edge distribution
   - false positive rate by latency
   - false positive rate by size
   - preliminary opportunity half-life estimate
4. Extend markdown reporting with recommendation-ready summary sections

### Definition Of Done

- replay reruns detector logic, not just log summarization
- replay can estimate false positives under latency assumptions
- report includes latency-tier results and net-edge decay metrics
- outputs are reproducible from stored logs and config

## Workstream 3: Makefile Compliance

### Goal

Bring the command surface closer to the assignment-standard deliverables.

### Required Additions

- `run_crypto`
- `replay_crypto`

If crypto remains out of scope for this repo version, these can be explicit placeholders that fail clearly with a short message instead of being absent.

### Recommended Additional Target

- `setup`

Suggested behavior:

- install dependencies
- print the main prediction-market commands

## Workstream 4: Week 3 Closeout

### Goal

Turn the 12-hour scanner run into documented evidence against the Week 3 acceptance criteria.

### Deliverables

- run logs saved to `logs/`
- short markdown summary in `reports/`
- key fields:
  - start time
  - end time
  - cycles completed
  - crashes
  - retries
  - flags emitted
  - notable API or data issues

### Definition Of Done

- scanner completes the intended 12-hour window without crashing
- run summary is written and reviewable
- any failures are categorized as code issues, API issues, or data-coverage issues

## Recommended Execution Order

1. Finish and document the 12-hour stability run
2. Complete the `open` snapshot pipeline
3. Upgrade replay into a latency-aware simulator
4. Add Makefile compliance targets
5. Refresh final reports and README

## Expected Result

At the end of this plan, the repo should support:

- all three required prediction timestamps: `open`, `mid`, `24h`
- a real replay path with latency-aware feasibility analysis
- stronger Week 3 and Week 4 evidence for review
- a cleaner assignment-facing command surface
