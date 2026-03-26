from __future__ import annotations

import json

from src.detect.scanner_core import flag_to_dict, scan_complement_market, scan_cross_venue_market
from src.config.scanner_fee_config import get_default_fee_config


FEE_CONFIG = get_default_fee_config()


def main() -> None:
    flags = []

    cross_flag = scan_cross_venue_market(
        market_id="btc-above-100k",
        buy_venue="polymarket",
        sell_venue="kalshi",
        buy_asks=[
            {"price": 0.60, "size": 60},
            {"price": 0.61, "size": 40},
        ],
        sell_bids=[
            {"price": 0.64, "size": 50},
            {"price": 0.63, "size": 50},
        ],
        target_size=100,
        fee_config=FEE_CONFIG,
        threshold_bps=100,
    )
    if cross_flag is not None:
        flags.append(flag_to_dict(cross_flag))

    complement_flag = scan_complement_market(
        market_id="election-yes-no",
        venue="polymarket",
        yes_asks=[{"price": 0.47, "size": 100}],
        no_asks=[{"price": 0.46, "size": 100}],
        target_size=100,
        fee_config=FEE_CONFIG,
        threshold_bps=100,
    )
    if complement_flag is not None:
        flags.append(flag_to_dict(complement_flag))

    print(json.dumps(flags, indent=2))


if __name__ == "__main__":
    main()