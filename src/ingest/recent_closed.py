from src.ingest.polymarket import run_polymarket_ingestion

if __name__ == "__main__":
    run_polymarket_ingestion(
        limit=20000,
        offset=10000,
        output_name="polymarket_markets_recent.parquet",
        raw_name="resolved_markets_recent.json",
    )