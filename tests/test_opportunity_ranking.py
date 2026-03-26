from pathlib import Path
import json
import shutil
import uuid

from src.detect.opportunity_ranking import (
    display_ranked_opportunities,
    net_edge_bps,
    rank_flags,
    write_ranked_snapshot,
)


def test_rank_flags_sorts_by_net_edge_bps():
    flags = [
        {"flag_type": "a", "details": {"net_edge_bps": 10.0, "net_edge": 0.01}},
        {"flag_type": "b", "details": {"net_edge_bps": 500.0, "net_edge": 0.05}},
        {"flag_type": "c", "details": {"net_edge_bps": 100.0, "net_edge": 0.02}},
    ]
    ranked = rank_flags(flags)
    assert [f["flag_type"] for f in ranked] == ["b", "c", "a"]


def test_net_edge_bps_missing():
    assert net_edge_bps({}) == float("-inf")
    assert net_edge_bps({"details": {}}) == float("-inf")


def test_write_ranked_snapshot():
    scratch = Path("artifacts/test_tmp") / f"rank_{uuid.uuid4().hex}"
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / "ranked.json"
    try:
        flags = [
            {"flag_type": "complement_sanity", "market_id": "M1", "details": {"net_edge_bps": 200.0, "net_edge": 0.02}},
        ]
        write_ranked_snapshot(rank_flags(flags), path, extra={"cycle_index": 3})
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["meta"]["cycle_index"] == 3
        assert len(data["ranked"]) == 1
        assert data["ranked"][0]["market_id"] == "M1"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_display_ranked_opportunities_writes_snapshot_when_configured():
    scratch = Path("artifacts/test_tmp") / f"rank_disp_{uuid.uuid4().hex}"
    scratch.mkdir(parents=True, exist_ok=True)
    out = scratch / "out.json"
    try:
        flags = [
            {
                "flag_type": "complement_sanity",
                "market_id": "M1",
                "question": "Test?",
                "details": {"net_edge_bps": 150.0, "net_edge": 0.015},
            },
        ]
        cfg = {"scanner": {"ranked_console_top_n": 5, "ranked_snapshot_path": str(out)}}
        display_ranked_opportunities(flags, config=cfg, title="t", cycle_index=1)
        assert out.exists()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
