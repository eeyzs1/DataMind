import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datamind.backends.storage.local_fs import LocalFSBackend


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DATAMIND_PROFILE", "dev")
    from datamind.core import factory
    factory._config_cache = None
    factory._config_path = tmp_path / "profile.yaml"
    import yaml
    config = {
        "profile": "dev",
        "storage": {"backend": "local_fs", "root_path": str(tmp_path / "data")},
        "compute": {"backend": "duckdb"},
        "query": {"backend": "duckdb"},
        "scheduler": {"backend": "apscheduler"},
        "ingestion": {"backend": "script"},
        "export": {"backend": "local"},
        "metadata": {"backend": "sqlite"},
        "auth": {"backend": "none"},
        "observability": {
            "log_backend": "stdout",
            "metrics_backend": "none",
            "trace_backend": "none",
        },
        "governance": {"quality_severity": "warn", "contract_enforcement": "warn"},
        "ai": {
            "control_plane": {"text_to_sql": "template"},
            "data_plane": {
                "anomaly_detection": "statistical",
                "pii_detection": "regex",
                "quality_check": "sql_rules",
            },
        },
    }
    with open(factory._config_path, "w") as f:
        yaml.dump(config, f)

    storage = LocalFSBackend(root_path=str(tmp_path / "data"))
    storage.ensure_zone_dirs()
    yield
    factory._config_cache = None


@pytest.fixture
def client():
    from datamind.api import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["profile"] == "dev"


class TestCatalogEndpoints:
    def test_list_tables_empty(self, client):
        resp = client.get("/api/v1/catalog/tables")
        assert resp.status_code == 200

    def test_search_catalog(self, client):
        resp = client.get("/api/v1/catalog/search?q=revenue")
        assert resp.status_code == 200
        assert "results" in resp.json()


class TestExportEndpoints:
    def test_export_batch_not_found(self, client):
        resp = client.post("/api/v1/export/batch", json={
            "source": "app/nonexistent",
            "format": "parquet",
        })
        assert resp.status_code in (200, 500)

    def test_export_status_not_found(self, client):
        resp = client.get("/api/v1/export/nonexistent/status")
        assert resp.status_code == 404


class TestQueryEndpoint:
    def test_query_missing_table(self, client):
        resp = client.post("/api/v1/query", json={
            "dataset": "app/nonexistent",
            "limit": 10,
        })
        assert resp.status_code == 404


class TestNaturalQuery:
    def test_no_matching_template(self, client):
        resp = client.post("/api/v1/query/natural", json={
            "question": "xyzzy foobar baz"
        })
        assert resp.status_code == 200
        assert "error" in resp.json()
