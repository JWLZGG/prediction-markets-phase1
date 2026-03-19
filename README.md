# Prediction Markets Phase 1

Phase 1 builds a snapshot-based prediction-market modeling and monitoring pipeline.

## Objective

Train on resolved historical markets, compare model performance against market-implied probabilities, select the strongest snapshot timing, and score current live markets.

## Main result

The 24h-before-close snapshot is the strongest modeling point in Phase 1.

- Midpoint snapshot adds smaller but positive signal
- Open snapshot is not currently robust enough
- Polymarket current scoring is cleaner and more trustworthy
- Kalshi current scoring is integrated, but still exploratory due to cross-venue domain shift

## Key deliverables

### Walkthrough
- `notebooks/day13_walkthrough.ipynb`

### Final reports
- `reports/final_model_report.md`
- `reports/current_monitor_report.md`
- `reports/offline_snapshot_summary.md`
- `reports/best_24h_coefficients.md`

### Key outputs
- `reports/offline_snapshot_summary.csv`
- `reports/best_24h_coefficients.csv`
- `reports/current_polymarket_top_edges_trained.csv`
- `reports/kalshi_current_top_edges_trained.csv`
- `reports/best_24h_model.pkl`

## Core commands

### Historical pipeline
```bash
python -m src.main features_recent
python -m src.main snapshots_recent
python -m src.main enrich_probs_recent
python -m src.main enrich_probs_mid_recent
python -m src.main enrich_probs_open_recent
python -m src.main enrich_history_24h_recent
python -m src.main enrich_history_mid_recent
python -m src.main integrity_checks_recent
Offline evaluation
python -m src.main evaluate_recent
python -m src.main evaluate_mid_recent
python -m src.main evaluate_narrow_history_recent_24hchange
python -m src.main summarize_offline_results
python -m src.main export_best_24h_coefficients
python -m src.main build_final_model_report
Best model training
python -m src.main train_best_24h_model
Current Polymarket scoring
python -m src.main ingest_current
python -m src.main features_current
python -m src.main score_current_polymarket_trained
Current Kalshi scoring
python -m src.main ingest_kalshi_current
python -m src.main features_kalshi_current
python -m src.main score_current_kalshi
Current monitor and sanity checks
python -m src.main sanity_check_current_scores
python -m src.main build_monitor_report
Testing
pytest tests/

## Phase 1 Deliverables

Phase 1 delivers a prediction-market modeling and monitoring prototype with:

### Core outputs
- `notebooks/day13_walkthrough.ipynb` — end-to-end walkthrough notebook
- `reports/final_model_report.md` — summary write-up of the modeling work
- `reports/current_monitor_report.md` — current monitor snapshot across venues
- `reports/offline_snapshot_summary.md` — open/mid/24h offline comparison
- `reports/best_24h_coefficients.md` — best-model coefficient interpretation

### Core machine-readable artifacts
- `reports/offline_snapshot_summary.csv`
- `reports/best_24h_coefficients.csv`
- `reports/current_polymarket_top_edges_trained.csv`
- `reports/kalshi_current_top_edges_trained.csv`
- `reports/best_24h_model.pkl`

### Core processed datasets
- `data/processed/features_mid_recent_history_enriched.parquet`
- `data/processed/features_24h_recent_history_enriched.parquet`
- `data/processed/current_polymarket_scored_trained.parquet`
- `data/processed/kalshi_current_scored_trained.parquet`

### Main conclusions
- The **24h snapshot** is the strongest modeling point.
- The model beats both naive and market baselines at **mid** and **24h**.
- **Polymarket** is the cleaner and more trustworthy current-monitor venue.
- **Kalshi** is integrated and filtered, but should still be treated as exploratory due to cross-venue domain shift.