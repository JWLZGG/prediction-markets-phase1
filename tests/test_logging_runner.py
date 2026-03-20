from pathlib import Path

from src.detect.logging_runner import build_synthetic_flags, write_flags_jsonl


def test_build_synthetic_flags_returns_flags():
    flags = build_synthetic_flags()
    assert len(flags) >= 1
    assert "flag_type" in flags[0]
    assert "market_id" in flags[0]


def test_write_flags_jsonl(tmp_path: Path):
    flags = build_synthetic_flags()
    log_path = tmp_path / "flags.jsonl"

    write_flags_jsonl(flags, log_path=log_path)

    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == len(flags)