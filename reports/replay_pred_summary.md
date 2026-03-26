# Replay Summary

- Flags input: 2
- Replay rows: 6
- Latency scenarios: [1, 5, 10]
- Average original net edge: 0.048622
- Estimated half-life (seconds): None

## By latency

| Latency (s) | Rows | Penalty (bps) | Avg replayed net edge | Median replayed net edge | False positive rate | Still positive rate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 5.0 | 0.047829 | 0.047829 | 0.0 | 1.0 |
| 5 | 2 | 15.0 | 0.046245 | 0.046245 | 0.0 | 1.0 |
| 10 | 2 | 30.0 | 0.043868 | 0.043868 | 0.0 | 1.0 |

## Conclusion

Replay v1 applies latency penalties to logged opportunities and estimates whether edge remains positive under delayed execution.
This is a first-pass feasibility framework and can later be upgraded with richer historical orderbook or quote evolution data.
