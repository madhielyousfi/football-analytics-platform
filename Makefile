PYTHON := .venv/bin/python
PIP := .venv/bin/pip
DBT := .venv/bin/dbt
STREAMLIT := .venv/bin/streamlit

.PHONY: install ingest dbt-run dbt-test dbt-build dashboard test pipeline api web web-build

api:
	$(PYTHON) -m uvicorn api.main:app --reload --port 8000

web:
	npm --prefix frontend run dev

web-build:
	npm --prefix frontend run build

demo-data:
	$(PYTHON) scripts/export_static_data.py --db data/demo.duckdb --out frontend/public/data

web-static: demo-data
	NEXT_PUBLIC_DATA_MODE=static npm --prefix frontend run build

install:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt

ingest:
	$(PYTHON) -m ingestion.run_ingestion

dbt-run:
	cd football_dbt && ../$(DBT) run --profiles-dir .

dbt-test:
	cd football_dbt && ../$(DBT) test --profiles-dir .

dbt-build:
	cd football_dbt && ../$(DBT) build --profiles-dir .

dashboard:
	$(STREAMLIT) run dashboard/app.py

test:
	$(PYTHON) -m pytest -q

pipeline: ingest dbt-build
