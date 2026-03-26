# Week 3 Status

## Completed

- Replay v1 implemented end-to-end in `src/backtest/replay_pred.py`
- Latency-aware replay scenarios added for 1s / 5s / 10s
- False-positive estimation implemented
- Replay outputs generated as:
  - `artifacts/outputs/replay_pred_rows.csv`
  - `artifacts/outputs/replay_pred_summary.json`
  - `reports/replay_pred_summary.md`
- Replay tests passing
- README updated with canonical replay command
- Live Polymarket complement detector already validated separately over long monitored runs

## Replay v1 result

Replay was run on a dedicated 4-flag sample set across 3 latency buckets.

- Flags input: 4
- Replay rows: 12
- Latency scenarios: 1s / 5s / 10s
- Average original net edge: 0.00875
- Estimated half-life: not yet observed under current penalty assumptions

### By latency

- 1s:
  - avg replayed net edge: 0.007963
  - false positive rate: 0.00
  - still positive rate: 1.00

- 5s:
  - avg replayed net edge: 0.006387
  - false positive rate: 0.25
  - still positive rate: 0.75

- 10s:
  - avg replayed net edge: 0.004025
  - false positive rate: 0.25
  - still positive rate: 0.75

## Interpretation

Replay v1 shows that edge decays under latency stress, and some marginal opportunities flip to false positives at higher latency assumptions. This validates the replay / feasibility framework and demonstrates that the scanner now has a working post-detection evaluation layer, even though the current implementation uses simplified penalty assumptions rather than full historical orderbook evolution.

## Conclusion

Week 3 deliverables are complete in practical v1 form.

At this point the project has:
- a stable live complement-detector branch
- long-run monitored detector validation
- executable pricing / fee / edge logic
- structured flag logging
- replay / latency-aware validation
- test-backed reporting outputs

## Remaining limitations

- Replay v1 currently uses penalty-based approximations rather than true historical orderbook evolution
- Cross-venue matched-market detection is scaffolded but blocked by the currently sports-dominated quoted Kalshi candidate universe
- Half-life was not reached in the current replay sample under the configured penalty schedule

## Recommended next branch

- either deepen replay realism with richer historical quote / orderbook evolution inputs
- or revisit cross-venue matching once a better non-sports Kalshi candidate universe is available