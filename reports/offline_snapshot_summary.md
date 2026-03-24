# Offline Snapshot Summary

This compares naive, market, and model Brier scores across open, mid, and 24h snapshots.



Open is reported using the practical v1 definition: first available observed price within 24 hours of market creation.

A strict 60-minute open definition is retained as a diagnostic only, and current history data supports very few such rows.



| snapshot | rows_used | strict_open_rows_60m | avg_minutes_from_open_to_snapshot | naive_brier | market_brier | model_brier | bss_vs_naive | bss_vs_market | takeaway |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| open | 248 | 1.000000 | 438.367350 | 0.250000 | 0.141263 | 0.112399 | 0.550406 | 0.204333 | model beats market |
| mid | 431 |  |  | 0.250000 | 0.073034 | 0.066788 | 0.732848 | 0.085518 | model beats market |
| 24h | 434 |  |  | 0.250000 | 0.046290 | 0.036890 | 0.852438 | 0.203064 | model beats market |

