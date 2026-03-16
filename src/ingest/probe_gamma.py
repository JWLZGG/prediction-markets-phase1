from __future__ import annotations

from src.ingest.polymarket import fetch_markets, save_probe, build_raw_markets_dataframe


def run_probe() -> None:
    probes = {
        "probe_default_closed": {
            "closed": "true",
            "limit": 50,
        },
        "probe_closed_active_false": {
            "closed": "true",
            "active": "false",
            "limit": 50,
        },
        "probe_closed_archived_false": {
            "closed": "true",
            "archived": "false",
            "limit": 50,
        },
        "probe_closed_order_desc": {
            "closed": "true",
            "order": "desc",
            "limit": 50,
        },
        "probe_closed_sort_end_desc": {
            "closed": "true",
            "sortBy": "endDate",
            "order": "desc",
            "limit": 50,
        },
        "probe_closed_sort_created_desc": {
            "closed": "true",
            "sortBy": "createdAt",
            "order": "desc",
            "limit": 50,
        },
    }

    for name, params in probes.items():
        try:
            raw = fetch_markets(limit=params.get("limit", 50), closed=True, extra_params=params)
            save_probe(name, raw)

            df = build_raw_markets_dataframe(raw)
            print(f"\n=== {name} ===")
            print(df[["market_id", "question", "created_at", "end_date"]].sort_values("end_date", ascending=False).head(10))
        except Exception as e:
            print(f"\n=== {name} FAILED ===")
            print(repr(e))


if __name__ == "__main__":
    run_probe()