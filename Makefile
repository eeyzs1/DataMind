.PHONY: setup-dev ingest etl export demo up-dev clean test

PYTHON ?= python
PIP ?= pip

setup-dev:
	$(PIP) install -e ".[dev]"
	$(PYTHON) scripts/init_data.py

ingest:
	$(PYTHON) scripts/init_data.py

etl:
	cd dbt_project && dbt run --profiles-dir .
	cd dbt_project && dbt test --profiles-dir .

export:
	$(PYTHON) -c "from datamind.core.factory import get_export; e=get_export(); e.export_file('app/app_daily_revenue', {'format':'parquet','target':'file','target_path':'exports/daily_revenue'}); print('Export done')"

up-api:
	uvicorn datamind.api:app --host 0.0.0.0 --port 8000 --reload

up-demo:
	streamlit run demo/app.py --server.port 8501

up-dev: up-api

demo:
	streamlit run demo/app.py --server.port 8501

clean:
	rm -rf data/cleaned data/detail data/summary data/app data/exports
	rm -f data/datamind.duckdb data/metadata.db

test:
	pytest tests/ -v

check-leak:
	@echo "Checking for interface leaks..."
	@grep -rn "import duckdb\|import boto3\|from pyspark\|import minio\|from kafka" --include="*.py" --exclude-dir=backends --exclude-dir=tests datamind/ api/ && echo "FAIL: Interface leak detected!" && exit 1 || echo "OK: No interface leaks"
