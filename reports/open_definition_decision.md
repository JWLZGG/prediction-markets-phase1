# Open Snapshot Definition Decision

## Decision

Treat the strict 60-minute `open` definition as the canonical acceptance metric.

Keep the practical v1 `first observed price within 24 hours of market creation` definition as a secondary exploratory metric only.

## Why

Mario's original specification for `open` was explicit:

- first available price within 60 minutes of market creation

Using the 24-hour fallback as the main `open` metric creates silent spec drift. It gives a useful research signal, but it is not the same target.

## Current Repo State

- The strict 60-minute selection logic exists in `src/features/open_snapshot_selection.py`.
- The current offline report uses the practical v1 fallback for the main `open` row.
- The current report also states that strict 60-minute support is extremely sparse in the available history data.

## Recommendation

For boss-facing and acceptance-criteria reporting:

1. label the strict 60-minute definition as the canonical `open`
2. report the practical 24-hour fallback separately as `open_v1_fallback` or similar
3. do not present the fallback metric as if it fully satisfies the original `open` requirement

## Implication

This means:

- `mid` and `24h` are clearly in good shape
- `open` is operationally useful in practical-v1 form
- the strict original `open` requirement should still be treated as partially unmet until data coverage improves
