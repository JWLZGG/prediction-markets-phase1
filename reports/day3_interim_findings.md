# Day 3 Interim Findings – Prediction Market Phase 1

## What is now working
I built a recent-market research pipeline for resolved Polymarket binary markets that:

- ingests and cleans recent resolved markets
- labels binary outcomes
- creates snapshot datasets at:
  - open
  - midpoint
  - 24h before close
- attaches market-implied probabilities from token-level price history
- benchmarks a logistic regression baseline against the raw market baseline using Brier score
- generates calibration / reliability outputs

## Current datasets
- markets_recent.parquet: 489 recent resolved markets
- features_24h_recent_enriched.parquet: 453 rows with non-null market-implied probabilities
- features_mid_recent_enriched.parquet: 450 rows with non-null market-implied probabilities
- features_open_recent_enriched.parquet: 0 rows with non-null market-implied probabilities under the strict at-or-before-open rule

## Current benchmark results

### 24h-before-close
- Model Brier score: 0.039203
- Market baseline Brier score: 0.042071

Result: the model slightly outperforms the raw market baseline on this recent 24h test set.

### Midpoint
- Model Brier score: 0.069323
- Market baseline Brier score: 0.065621

Result: the market baseline outperforms the model at midpoint.

## Interpretation
- Market-implied probability is by far the dominant feature.
- Duration and category currently add very little incremental signal.
- This suggests the current model is largely a light adjustment on top of market odds.
- The 24h snapshot may still contain exploitable structure for a simple model.
- The midpoint snapshot appears more market-efficient under the current feature set.

Current feature importance is dominated by `market_implied_prob`.

The present model is effectively driven by:
- `market_implied_prob`
- a very small contribution from `duration_hours`

Current non-market features are still weak:
- `category` is entirely missing in the recent dataset (`None` for all rows)
- `volume` and `liquidity` are not yet present in the enriched snapshot files

So the current model should be interpreted as a market-odds benchmark plus a very light adjustment, rather than a richer multi-feature model.


## Open snapshot limitation
Strict open enrichment currently fails because, for sampled recent markets, the earliest returned price-history point begins after the market open timestamp. This means a true open snapshot is not currently observable from the available history under the strict methodology.

## Next steps
1. Improve feature set beyond market probability, duration and category.
2. Inspect category quality / missingness.
3. Add simple price-path features (momentum, recent change, volatility, number of history points).
4. Re-run 24h and midpoint evaluations with stronger features.
5. Decide whether to keep strict open unavailable or add a clearly labeled proxy-open fallback using the earliest post-open observation.

# Day 3 Interim Findings – Prediction Market Phase 1

## What is now working
I built a recent-market research pipeline for resolved Polymarket binary markets that:

- ingests and cleans recent resolved markets
- labels binary outcomes
- creates snapshot datasets at:
  - open
  - midpoint
  - 24h before close
- attaches market-implied probabilities from token-level price history
- benchmarks a logistic regression baseline against the raw market baseline using Brier score
- generates calibration / reliability outputs

## Current datasets
- `markets_recent.parquet`: 489 recent resolved markets
- `features_24h_recent_enriched.parquet`: 453 rows with non-null market-implied probabilities
- `features_mid_recent_enriched.parquet`: 450 rows with non-null market-implied probabilities
- `features_open_recent_enriched.parquet`: 0 rows with non-null market-implied probabilities under the strict at-or-before-open rule

## Current benchmark results

### 24h-before-close
- Model Brier score: 0.039203
- Market baseline Brier score: 0.042071

Result: the model slightly outperforms the raw market baseline on this recent 24h test set.

### Midpoint
- Model Brier score: 0.069323
- Market baseline Brier score: 0.065621

Result: the market baseline outperforms the model at midpoint.

## Calibration / reliability
Calibration plots have been generated for:
- `reports/calibration_recent_24h.png`
- `reports/calibration_recent_mid.png`

These provide a first check of whether predicted probabilities line up with observed event frequencies.

## Feature interpretation
Current feature importance is dominated by `market_implied_prob`.

The present model is effectively driven by:
- `market_implied_prob`
- a very small contribution from `duration_hours`

Current non-market features are still weak:
- `category` is entirely missing in the recent dataset (`None` for all rows)
- `volume` and `liquidity` are not yet present in the enriched snapshot files

So the current model should be interpreted as a market-odds benchmark plus a very light adjustment, rather than a richer multi-feature model.

## Open snapshot limitation
Strict open enrichment currently has zero coverage because, for sampled recent markets, the earliest returned price-history point begins after the market open timestamp.

This means a true open snapshot is not currently observable from the available history under the strict methodology.

## Interpretation
- The pipeline is now working end to end for recent markets.
- 24h-before-close may still contain slight incremental signal beyond raw market odds.
- Midpoint appears more market-efficient under the current simple feature set.
- The next gains are likely to come from better features and better data coverage, rather than retuning the same baseline.

## Next steps
1. Carry `volume` and `liquidity` through into snapshot and enriched files.
2. Improve feature set beyond market probability and duration.
3. Add simple price-path features where feasible.
4. Re-run 24h and midpoint evaluations with stronger features.
5. Decide whether to keep strict open unavailable or add a clearly labeled proxy-open fallback using the earliest post-open observation.# Day 3 Interim Findings – Prediction Market Phase 1

## What is now working
I built a recent-market research pipeline for resolved Polymarket binary markets that:


- ingests and cleans recent resolved markets
- labels binary outcomes
- creates snapshot datasets at:
  - open
  - midpoint
  - 24h before close
- attaches market-implied probabilities from token-level price history
- benchmarks a logistic regression baseline against the raw market baseline using Brier score
- generates calibration / reliability outputs

## Current datasets
- `markets_recent.parquet`: 489 recent resolved markets
- `features_24h_recent_enriched.parquet`: 453 rows with non-null market-implied probabilities
- `features_mid_recent_enriched.parquet`: 450 rows with non-null market-implied probabilities
- `features_open_recent_enriched.parquet`: 0 rows with non-null market-implied probabilities under the strict at-or-before-open rule

## Current benchmark results

### 24h-before-close
- Model Brier score: 0.039203
- Market baseline Brier score: 0.042071

Result: the model slightly outperforms the raw market baseline on this recent 24h test set.

### Midpoint
- Model Brier score: 0.069323
- Market baseline Brier score: 0.065621

Result: the market baseline outperforms the model at midpoint.

## Calibration / reliability
Calibration plots have been generated for:
- `reports/calibration_recent_24h.png`
- `reports/calibration_recent_mid.png`

These provide a first check of whether predicted probabilities line up with observed event frequencies.

## Feature interpretation
Current feature importance is dominated by `market_implied_prob`.

The present model is effectively driven by:
- `market_implied_prob`
- a very small contribution from `duration_hours`

Current non-market features are still weak:
- `category` is entirely missing in the recent dataset (`None` for all rows)
- `volume` and `liquidity` are not yet present in the enriched snapshot files

So the current model should be interpreted as a market-odds benchmark plus a very light adjustment, rather than a richer multi-feature model.

## Open snapshot limitation
Strict open enrichment currently has zero coverage because, for sampled recent markets, the earliest returned price-history point begins after the market open timestamp.

This means a true open snapshot is not currently observable from the available history under the strict methodology.

## Interpretation
- The pipeline is now working end to end for recent markets.
- 24h-before-close may still contain slight incremental signal beyond raw market odds.
- Midpoint appears more market-efficient under the current simple feature set.
- The next gains are likely to come from better features and better data coverage, rather than retuning the same baseline.

## Next steps
1. Carry `volume` and `liquidity` through into snapshot and enriched files.
2. Improve feature set beyond market probability and duration.
3. Add simple price-path features where feasible.
4. Re-run 24h and midpoint evaluations with stronger features.
5. Decide whether to keep strict open unavailable or add a clearly labeled proxy-open fallback using the earliest post-open observation.





