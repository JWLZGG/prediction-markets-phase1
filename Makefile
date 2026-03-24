install:
	pip install -r requirements.txt

ingest_current:
	python -m src.main ingest_current

ingest_kalshi_current:
	python -m src.main ingest_kalshi_current

ingest_polymarket_orderbooks:
	python -m src.main ingest_polymarket_orderbooks

test:
	pytest tests/

run_pred:
	python -m src.main run_pred

run_pred_synth:
	python -m src.main run_pred --mode synthetic

run_pred_kalshi_complement:
	python -m src.main run_pred --mode live_complement

run_pred_polymarket_complement:
	python -m src.main run_pred --mode live_complement_polymarket

evaluate:
	python -m src.main evaluate

replay_pred:
	python -m src.main replay_pred

scanner_status:
	python -m src.main scanner_status

run_crypto:
	@echo "run_crypto not implemented in this repo version"

replay_crypto:
	@echo "replay_crypto not implemented in this repo version"

setup:
	@echo "Use the project virtual environment and install dependencies per README"

run_pred:
	python -m src.detect.prediction_scanner --mode live_complement_polymarket_loop

replay_pred:
	python -m src.backtest.replay_pred