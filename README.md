install:
	pip install -r requirements.txt

ingest:
	python -m src.main ingest

features:
	python -m src.main features

model:
	python -m src.main model

test:
	pytest tests/