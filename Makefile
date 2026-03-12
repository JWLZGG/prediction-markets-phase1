install:
	pip install -r requirements.txt

ingest:
	python -m src.main ingest

features:
	python -m src.main features

test:
	pytest tests/