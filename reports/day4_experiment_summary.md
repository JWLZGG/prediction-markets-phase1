# Day 4 Experiment Summary

## Objective
Test whether first-pass history-derived probability-path features improve forecast performance beyond the market's own implied probability.

## Dataset
- Source: filtered recent resolved Polymarket markets
- Volume threshold: >= 1000
- Recent filtered market count: 470
- 24h rows used in modelling: 434
- Mid rows used in modelling: 431

## Models compared

| Experiment | Snapshot | Rows | Feature set | Model Brier | Market Brier | Result |
|---|---:|---:|---|---:|---:|---|
| simple_baseline_24h | 24h | 434 | market_implied_prob + duration_hours + log_volume + log_liquidity + category_fallback | 0.051627 | 0.052364 | model slightly beats market |
| history_baseline_24h | 24h | 434 | simple features + distance_from_0_5 + prob_change_24h + prob_change_12h + realized_volatility + history_points_count | 0.053923 | 0.052364 | worse than market |
| simple_baseline_mid | mid | 431 | market_implied_prob + duration_hours + log_volume + log_liquidity + category_fallback | 0.073328 | 0.070879 | worse than market |
| history_baseline_mid | mid | 431 | simple features + distance_from_0_5 + prob_change_24h + prob_change_12h + realized_volatility + history_points_count | 0.072874 | 0.070879 | improved vs simple mid, still worse than market |

## Interpretation
- The market-implied probability remains the dominant signal.
- The current best-performing model is the simple 24h baseline.
- Adding the first-pass history/path features hurt 24h performance.
- Adding the same history/path features improved midpoint performance slightly relative to the simpler midpoint model, but not enough to beat the market baseline.

## Current best result
- Best model so far: simple_baseline_24h
- Best Brier score: 0.051627

## Notes
- The recent pipeline now includes formal filtering rules, a minimum volume threshold, fallback category assignment, stratified sampling, snapshot generation, market-probability enrichment, calibration diagnostics, and experiment logging.
- Liquidity remains too sparse to be a reliable filter at this stage.

## Next experiment direction
Rather than broad history bundles, the next iteration should test a narrower trailing-window feature set:
- short-horizon momentum
- trailing probability range
- trailing volatility over a recent window
- time since last price update
- fraction of lifecycle elapsed

## Day 5 will test narrower trailing-window history features rather than the broader first-pass history bundle.