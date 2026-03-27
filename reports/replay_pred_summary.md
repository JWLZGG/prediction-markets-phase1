# Replay Summary

- Flags input: 6
- Replay rows: 18
- Observed-state rows: 0
- Replayable rows: 0
- Latency scenarios: [1, 5, 10]
- Average original net edge: 0.022041
- Estimated half-life (seconds): None

## Status counts

| Replay status | Rows |
|---|---:|
| unsupported_no_observed_state_path | 18 |

## By latency

| Latency (s) | Rows | Observed-state rows | Replayable rows | Missing later snapshot | Insufficient later liquidity | Unsupported rows | Avg replayed net edge | Median replayed net edge | False positive rate | Still positive rate |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 6 | 0 | 0 | 0 | 0 | 6 | None | None | None | None |
| 5 | 6 | 0 | 0 | 0 | 0 | 6 | None | None | None | None |
| 10 | 6 | 0 | 0 | 0 | 0 | 6 | None | None | None | None |

## By size and latency

| Size bucket | Latency (s) | Rows | Replayable rows | False positive rate | Still positive rate |
|---|---:|---:|---:|---:|---:|
| medium | 1 | 6 | 0 | None | None |
| medium | 5 | 6 | 0 | None | None |
| medium | 10 | 6 | 0 | None | None |

## Conclusion

Replay now prefers observed later-state snapshots for supported Polymarket complement flags.
Rows without a later snapshot or without replayable live metadata are kept in the output with explicit statuses instead of being silently penalized by a proxy model.
