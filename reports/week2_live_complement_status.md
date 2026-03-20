# Week 2 Live Complement Status

## Summary

The core detector primitives are now complete and tested:

- executable pricing / book walking
- fee model
- slippage-aware edge logic
- scanner core
- synthetic cross-venue and complement detection
- JSONL flag logging
- synthetic mode integrated into `prediction_scanner.py`

A first real live executable detector path has also been added:

- `--mode live_complement`
- current implementation targets Kalshi complement-sanity detection

## Current live Kalshi complement coverage

Latest observed stats from `python -m src.detect.prediction_scanner --mode live_complement`:

- active binary rows: 3000
- usable YES side: 505
- usable NO side: 6
- usable both sides: 3
- eligible top book: 3
- sufficient size: 3
- emitted flags: 0

## Interpretation

The live complement detector path is functioning correctly on real current venue data, but current Kalshi snapshot coverage is too sparse for meaningful long-run detector validation.

The bottleneck is not the detector logic itself. The bottleneck is live executable two-sided quote coverage, especially on the NO side.

## Conclusion

At this stage:

- detector primitives are complete
- live Kalshi complement mode is implemented
- real live detection has begun
- however, current snapshot coverage is too sparse to justify:
  - a long detector-specific stability run
  - real executable detection running for hours in a meaningful way
  - a full 12-hour monitored run of the executable detector

## Recommended next step

Upgrade live ingestion to capture richer executable book data from Kalshi and/or Polymarket so that complement or cross-venue detection can operate over a meaningfully larger live market set.