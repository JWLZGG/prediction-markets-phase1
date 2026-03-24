from pathlib import Path
import shutil
import uuid

from src.detect.logging_runner import build_synthetic_flags, write_flags_jsonl


def test_build_synthetic_flags_returns_flags():
    flags = build_synthetic_flags()
    assert len(flags) >= 1
    assert "flag_type" in flags[0]
    assert "market_id" in flags[0]


def test_write_flags_jsonl():
    flags = build_synthetic_flags()
    scratch_dir = Path("artifacts/test_tmp") / f"logging_{uuid.uuid4().hex}"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    log_path = scratch_dir / "flags.jsonl"

    try:
        write_flags_jsonl(flags, log_path=log_path, source="unit_test")

        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == len(flags)
        assert '"source": "unit_test"' in lines[0]
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)
