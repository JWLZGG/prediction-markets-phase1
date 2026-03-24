from pathlib import Path
import shutil
import uuid

from src.backtest.replay_pred import build_replay_summary, render_replay_report


def test_build_replay_summary_handles_logs():
    scratch_dir = Path("artifacts/test_tmp") / f"replay_{uuid.uuid4().hex}"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    flags_log = scratch_dir / "flags.jsonl"
    runs_log = scratch_dir / "runs.jsonl"
    polymarket_runs_log = scratch_dir / "poly_runs.jsonl"

    try:
        flags_log.write_text(
            "\n".join(
                [
                    '{"timestamp":"2026-03-24T00:00:00+00:00","source":"kalshi_live_complement","flag_type":"complement_sanity","market_id":"M1","details":{"net_edge_bps":120.0}}',
                    '{"timestamp":"2026-03-24T00:01:00+00:00","source":"polymarket_live_complement","flag_type":"complement_sanity","market_id":"M2","details":{"net_edge_bps":250.0}}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        runs_log.write_text(
            '{"ts_utc":"2026-03-24T00:00:00+00:00","cycle_index":1}\n',
            encoding="utf-8",
        )
        polymarket_runs_log.write_text(
            '{"ts_utc":"2026-03-24T00:02:00+00:00","cycle_index":1}\n',
            encoding="utf-8",
        )

        summary = build_replay_summary(
            flags_log_path=flags_log,
            runs_log_path=runs_log,
            polymarket_runs_log_path=polymarket_runs_log,
        )

        assert summary.total_flags == 2
        assert summary.total_run_cycles == 1
        assert summary.total_polymarket_complement_cycles == 1
        assert summary.unique_markets_flagged == 2
        assert summary.best_flag_market_id == "M2"
        assert summary.best_net_edge_bps == 250.0
        assert summary.flag_counts_by_source["kalshi_live_complement"] == 1
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


def test_render_replay_report_includes_key_counts():
    scratch_dir = Path("artifacts/test_tmp") / f"replay_empty_{uuid.uuid4().hex}"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    try:
        summary = build_replay_summary(
            flags_log_path=scratch_dir / "missing_flags.jsonl",
            runs_log_path=scratch_dir / "missing_runs.jsonl",
            polymarket_runs_log_path=scratch_dir / "missing_poly_runs.jsonl",
        )

        report = render_replay_report(summary)

        assert "# Replay Summary" in report
        assert "- Total flags: `0`" in report
        assert "## Flags By Type" in report
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)
