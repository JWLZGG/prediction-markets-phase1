# Replay Summary

Phase B scaffold: latency-labelled replay using deterministic logged-state recomputation.

Current replay mode is `deterministic_proxy`, which means recomputation uses the logged detector inputs rather than a later observed market state.
This is the correct intermediate step before wiring true `t + latency` snapshot lookups.

- Total replay rows: 6
- Consistent recomputations: 6
- Still-positive count: 6
- False-positive count: 0

## By latency

### 250ms
- Total: 2
- Consistent: 2
- Still positive: 2
- False positive: 0

### 1s
- Total: 2
- Consistent: 2
- Still positive: 2
- False positive: 0

### 3s
- Total: 2
- Consistent: 2
- Still positive: 2
- False positive: 0

## Detailed results

| latency | replay_mode | flag_type | market_id | original_net_edge | recomputed_net_edge | edge_diff | still_positive | false_positive | consistent | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 250ms | deterministic_proxy | cross_venue_divergence | btc-above-100k | 0.028174 | 0.028173 | -0.000001 | True | False | True | ok |
| 1s | deterministic_proxy | cross_venue_divergence | btc-above-100k | 0.028174 | 0.028173 | -0.000001 | True | False | True | ok |
| 3s | deterministic_proxy | cross_venue_divergence | btc-above-100k | 0.028174 | 0.028173 | -0.000001 | True | False | True | ok |
| 250ms | deterministic_proxy | complement_sanity | election-yes-no | 0.069070 | 0.069070 | 0.000000 | True | False | True | ok |
| 1s | deterministic_proxy | complement_sanity | election-yes-no | 0.069070 | 0.069070 | 0.000000 | True | False | True | ok |
| 3s | deterministic_proxy | complement_sanity | election-yes-no | 0.069070 | 0.069070 | 0.000000 | True | False | True | ok |