# 12-Hour Stability Run Summary

## Run Metadata

- Date: March 25-26, 2026
- Start time (local): 2026-03-25 13:02:59 AEDT
- End time (local): 2026-03-26 09:29:20 AEDT
- Total wall-clock duration: 20.439 hours across the inspected complement run log file
- Operator: Jeremy Chan
- Command used: `python -m src.detect.prediction_scanner --mode live_complement_polymarket_loop`
- Config file: `configs/prediction_scanner.yaml`
- Git commit or branch: `main`

## Scanner Configuration

- Mode: `live_complement_polymarket_loop`
- Loop interval seconds: `60`
- Max cycles configured: `360`
- Target size: `10.0`
- Threshold bps: `10.0`
- Market limit: `100`
- Flag log path: `logs/polymarket_complement_flags.jsonl`
- Run log path: `logs/polymarket_complement_runs.jsonl`
- Snapshot path pattern: `data/processed/polymarket_orderbooks_snapshots/polymarket_orderbooks_*.parquet`

## Outcome Summary

- Completed 12-hour window: Operationally yes from the combined run log, with a documentation caveat
- Crash count: `0` logged
- Manual restarts: session boundaries are mixed in the same JSONL log, so exact restarts are not isolated cleanly
- Cycles completed: `764` logged complement cycles in the inspected run log file
- Successful cycles: `764`
- Failed cycles: `0`
- Total flags emitted: `0`
- Unique markets flagged: `0`

## Error And Retry Summary

- Total warnings: not explicitly counted from stored logs
- Total retries: not explicitly counted from stored logs
- API failures observed: `0` cycle-level failures logged
- Data-shape failures observed: `0` cycle-level failures logged
- File write failures observed: `0` cycle-level failures logged
- Other errors: none logged at cycle level

## Replay Readiness

- Timestamped snapshots written: Yes
- Replayable flag rows produced: No
- Replay log used: `reports/replay_pred_summary.md`
- Notes on replay coverage:
  - `601` timestamped Polymarket orderbook snapshots are present.
  - The strongest clean snapshot-backed session reconstructed from filenames spans `11.254` hours.
  - Current observed-state replay code is ready, but no live Polymarket complement flags were emitted, so there are no replayable live rows yet.

## Key Observations

- The scanner loop was operationally stable over a long window and logged zero cycle-level errors.
- No complement-sanity opportunities were emitted during the inspected runs.
- Log hygiene is the main caveat: the JSONL run file contains multiple sessions, so the cleanest single-session proof is weaker than the total operational span in the file.

## Acceptance Criteria Assessment

### Scanner runs for 12 hours without crash

Status: Partially demonstrated

Evidence:
- `logs/polymarket_complement_runs.jsonl` spans `20.439` hours with `0` logged cycle-level errors.
- Timestamped snapshot sessions confirm long clean runs, but the longest clean snapshot-backed single session currently reconstructs to `11.254` hours rather than a neatly isolated `12+` hour block.

### Logs opportunity events with full reproducibility

Status: Partially met

Evidence:
- Run logs and snapshot retention are present.
- Live Polymarket complement flags did not occur during the inspected runs, so there were no replayable live flag rows to validate end-to-end.

### Shows ranked or reviewable outputs

Status: Met

Evidence:
- Ranked review/report outputs exist elsewhere in the repo, and the scanner runtime supports ranked console display when flags are present.

## Follow-Up Actions

1. Run one clean single-session 12+ hour complement loop with a dedicated fresh log file to remove the session-mixing caveat.
2. Add real matched cross-venue market pairs or broaden the live monitor universe so the scanner can emit replayable live flags.
3. Use the new observed-state replay path once live complement or matched cross-venue flags exist.
