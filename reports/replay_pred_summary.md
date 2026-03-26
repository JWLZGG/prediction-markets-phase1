# Replay Summary

- Flags input: 4
- Replay rows: 12
- Latency scenarios: [1, 5, 10]
- Average original net edge: 0.00875
- Estimated half-life (seconds): None

## By latency

| Latency (s) | Rows | Penalty (bps) | Avg replayed net edge | Median replayed net edge | False positive rate | Still positive rate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 4 | 5.0 | 0.007963 | 0.006418 | 0.0 | 1.0 |
| 5 | 4 | 15.0 | 0.006387 | 0.005254 | 0.25 | 0.75 |
| 10 | 4 | 30.0 | 0.004025 | 0.003508 | 0.25 | 0.75 |

## Conclusion

Replay v1 applies latency penalties to logged opportunities and estimates whether edge remains positive under delayed execution.
This is a first-pass feasibility framework and can later be upgraded with richer historical orderbook or quote evolution data.
