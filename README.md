# Prediction Markets Phase 1

Prediction Markets Phase 1 is a forecasting and detector prototype for prediction markets, focused on two venues:

- **Polymarket**
- **Kalshi**

The repo currently contains two working layers:

1. a **historical forecasting / ML pipeline**
2. a **detector / scanner core** for executable opportunity logic

---

## Overview

The project began as a Phase 1 modelling pipeline: ingest resolved markets, build timestamp-safe snapshots, train a baseline forecasting model, compare it against market-implied probabilities and score current markets.

It has since expanded into a scanner prototype with:

- executable book-walking
- fee and slippage-aware cost modelling
- edge computation
- structured JSONL logging
- synthetic and live scanner modes

The current state is best described as:

- **forecasting pipeline: working**
- **detector primitives: working**
- **first live executable detection: working, but coverage-limited**
- **replay and larger-scale live executable monitoring: still in progress**

---

## Current Status

## 1. Forecasting / ML layer

Implemented:

- historical market ingestion and normalisation
- snapshot feature generation at:
  - market open
  - midpoint
  - 24h-before-close
- timestamp integrity and leakage checks
- baseline logistic regression training
- holdout Brier-score evaluation
- coefficient / feature interpretation
- current market scoring for Polymarket and Kalshi

Current takeaway:

- the **24h-before-close snapshot** is the strongest current modelling point
- the baseline model is only modestly better than market baseline, which is expected for a first logistic model in prediction markets
- **Polymarket** current scoring is cleaner and more trustworthy
- **Kalshi** current scoring is integrated but still more exploratory

---

## 2. Detector / scanner layer

Implemented:

- executable pricing / book-walking
- fee and slippage-aware cost model
- cross-venue edge computation
- complement-sanity edge computation
- scanner core
- synthetic cross-venue and complement detection
- structured JSONL flag logging
- synthetic and live scanner modes
- first live Kalshi complement integration

Current takeaway:

- detector primitives are now implemented and tested
- the scanner can emit structured flags and log them
- first live executable detection has started
- current **Kalshi snapshot coverage is too sparse** for meaningful long-run executable monitoring at scale
- the next major step is richer live order-book ingestion, especially for Polymarket and/or a richer Kalshi depth source

---

## Canonical Repo Structure

```text
src/
  ingest/
  features/
  detect/
  backtest/
  models/
  utils/
  experimental/

tests/
configs/
reports/
artifacts/
notebooks/
data/   # gitignored

### Canonical Commands
These are the main commands that reflect the current working path.
## Baseline training

```text
python -m src.models.baseline_logreg

## Offline evaluation

```text
python -m src.models.evaluate

## Current market scoring

```text
python -m src.models.score_current_polymarket
python -m src.models.score_current_kalshi

## Scanner modes

```text
python -m src.detect.prediction_scanner --mode synthetic
python -m src.detect.prediction_scanner --mode live
python -m src.detect.prediction_scanner --mode live_complement

## Detector module demos

```text
python -m src.detect.executable_pricing
python -m src.detect.demo_scanner
python -m src.detect.logging_runner

## Tests

```text
pytest tests/ -q

## Key Outputs
## Reports

- reports/final_model_report.md

- reports/current_monitor_report.md

- reports/offline_snapshot_summary.md

- reports/best_24h_coefficients.md

- reports/week2_live_complement_status.md

## Notebook

- notebooks/day13_walkthrough.ipynb

## Artifacts

- artifacts/models/best_24h_model.pkl

- artifacts/outputs/current_polymarket_top_edges_trained.csv

- artifacts/outputs/kalshi_current_top_edges_trained.csv

- artifacts/outputs/best_24h_coefficients.csv

- artifacts/plots/

## Processed datasets

- data/processed/features_24h_recent_history_enriched.parquet

- data/processed/current_polymarket_scored_trained.parquet

- data/processed/kalshi_current_scored_trained.parquet

- data/processed/polymarket_markets_current.parquet

- data/processed/kalshi_markets_current.parquet

## Testing Coverage

The repo now includes unit-tested detector primitives for:

- executable book-walking

- fee computation

- edge computation

- scanner core

- logging wrapper

- Kalshi live complement adapter

This means the scanner foundation is no longer just conceptual; the core arithmetic and flagging logic are tested and reproducible.

## What Is Completed

At this point, the following are substantially complete:

- Phase 1 historical ingestion and feature-building pipeline

- leakage-safe snapshot generation

- baseline forecasting model training and evaluation

- current scoring for Polymarket and Kalshi

- executable pricing module

- fee and slippage-aware cost model

- edge computation

- synthetic scanner flags

- JSONL flag logging

- scanner entrypoint with multiple modes

- first live executable detector path on Kalshi complement markets

- repo cleanup into a clearer canonical structure

## What Is Still In Progress

The following are the main remaining gaps:

- richer live order-book ingestion for executable detection

- broader real-market live detector coverage

- live complement detection over a meaningfully larger market set

- cross-venue real matched-market detection

- replay / latency-aware validation

- false-positive estimation

- opportunity persistence / half-life analysis

- final end-to-end delivery packaging

## Current Limitation

The most important current blocker is live executable market coverage, not detector logic.

The detector itself is working. The current live Kalshi complement mode shows that:

active binary rows are available

many rows have usable YES-side information

very few rows have enough usable NO-side executable information

as a result, only a very small number of markets are currently eligible for live complement checks

This means the current live executable detector path is valid, but not yet broad enough to justify a meaningful long-run monitored session.

## Recommended Next Step

The highest-value next engineering step is:

upgrade live ingestion to fetch richer executable order-book data, most likely starting with Polymarket order books using clobTokenIds, then building a real live complement detector over that richer book data.

That will unlock:

- larger live executable market coverage

- more meaningful monitored detector runs

- better cross-venue detection potential

eventual replay / validation work on a stronger live opportunity stream

Notes for Reviewers

The easiest ways to review this work today are:

- read the notebook: notebooks/day13_walkthrough.ipynb

- read the reports in reports/

- clone the repo and run the canonical commands above

- inspect the detector logs in logs/

The current repo is intended to be honest about scope:

- the forecasting layer is further along

- the detector-core engineering is now in place

- the main remaining challenge is richer live executable-book ingestion and downstream validation
