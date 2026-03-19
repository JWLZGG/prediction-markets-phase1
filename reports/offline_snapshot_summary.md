# Offline Snapshot Summary

This compares naive, market, and model Brier scores across open, mid, and 24h snapshots.

| snapshot | rows_used | naive_brier | market_brier | model_brier | bss_vs_naive | bss_vs_market | takeaway |
| --- | --- | --- | --- | --- | --- | --- | --- |
| open | 0 |  |  |  |  |  | no usable rows |
| mid | 431 | 0.250000 | 0.073034 | 0.066848 | 0.732606 | 0.084691 | model beats market |
| 24h | 434 | 0.250000 | 0.046290 | 0.036892 | 0.852431 | 0.203027 | model beats market |

