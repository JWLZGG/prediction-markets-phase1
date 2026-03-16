# Phase 1 Success Criteria

## Goal
Build a reproducible historical prediction-market research pipeline that can test whether simple models can improve on the market's own implied probabilities at different points in the market lifecycle.

## Phase 1 is considered successful if it includes:

### 1. Reproducible data pipeline
- ingest recent resolved market data
- persist raw and processed datasets
- rebuild outputs deterministically from the codebase

### 2. Clean modelling universe
- resolved binary markets only
- timestamp sanity checks
- formal minimum volume threshold
- labelled outcomes available
- documented exclusions and limitations

### 3. Snapshot generation
- one row per market per snapshot
- snapshots at:
  - open
  - midpoint
  - 24h before close
- fields at each snapshot restricted to information available at that time

### 4. Market probability enrichment
- attach contemporaneous market-implied probabilities from token price history
- record coverage and missingness by snapshot type

### 5. Benchmarkable evaluation framework
- compare model probabilities directly against market-implied probabilities
- use Brier score as the primary metric
- inspect calibration / reliability
- inspect feature coefficients for basic interpretation

### 6. Experiment tracking
- maintain a compact experiment log with:
  - experiment name
  - snapshot
  - features used
  - rows used
  - model Brier
  - market Brier
  - takeaway

### 7. Clear research outcome
Phase 1 does not need to prove a large edge.
It needs to establish:
- where a simple model may help
- where the market remains stronger
- which feature directions are worth testing next

## Current Phase 1 status
- Pipeline: in place
- Recent filtered labelled dataset: in place
- Snapshot generation: in place
- Probability enrichment: in place for 24h and midpoint
- Benchmarking and calibration: in place
- Experiment log: in place
- Current best result: simple 24h model slightly beats market baseline
- Main limitation: current feature engineering still relies heavily on market-implied probability, and first-pass history features do not yet add robust incremental edge