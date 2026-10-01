PYTHON := .venv/bin/python
PIP := .venv/bin/pip
DBT := .venv/bin/dbt
STREAMLIT := .venv/bin/streamlit

.PHONY: install ingest dbt-run dbt-test dbt-build dashboard test pipeline

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
