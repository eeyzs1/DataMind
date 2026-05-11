import os
import tempfile

import pandas as pd
import pytest

from datamind.backends.compute.duckdb_engine import DuckDBEngine
from datamind.backends.export.local_export import LocalExport
from datamind.backends.metadata.sqlite_store import SQLiteStore
from datamind.backends.storage.local_fs import LocalFSBackend


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def storage(tmp_dir):
    backend = LocalFSBackend(root_path=tmp_dir)
    backend.ensure_zone_dirs()
    return backend


@pytest.fixture
def compute():
    engine = DuckDBEngine()
    yield engine
    engine.close()


@pytest.fixture
def metadata(tmp_dir):
    store = SQLiteStore(db_path=os.path.join(tmp_dir, "metadata.db"))
    yield store
    store.close()


class TestStorageContract:
    def test_write_and_read(self, storage):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        storage.write_parquet(df, "raw/test_table")
        result = storage.read_parquet("raw/test_table")
        assert len(result) == 3
        assert list(result.columns) == ["a", "b"]

    def test_exists(self, storage):
        assert not storage.exists("raw/nonexistent")
        df = pd.DataFrame({"x": [1]})
        storage.write_parquet(df, "raw/exists_test")
        assert storage.exists("raw/exists_test")

    def test_list_tables(self, storage):
        df = pd.DataFrame({"x": [1]})
        storage.write_parquet(df, "raw/table_a")
        storage.write_parquet(df, "raw/table_b")
        tables = storage.list_tables("raw")
        assert "table_a" in tables
        assert "table_b" in tables

    def test_overwrite_mode(self, storage):
        df1 = pd.DataFrame({"a": [1]})
        storage.write_parquet(df1, "raw/overwrite_test")
        df2 = pd.DataFrame({"a": [2, 3]})
        storage.write_parquet(df2, "raw/overwrite_test", mode="overwrite")
        result = storage.read_parquet("raw/overwrite_test")
        assert len(result) == 2

    def test_data_path(self, storage):
        path = storage.data_path("raw/orders")
        assert "raw" in path
        assert "orders" in path


class TestComputeContract:
    def test_execute(self, compute):
        df = compute.execute("SELECT 1 AS a, 'hello' AS b")
        assert len(df) == 1
        assert df.iloc[0]["a"] == 1

    def test_register_table(self, storage, compute):
        df = pd.DataFrame({"id": [1, 2], "value": [10, 20]})
        storage.write_parquet(df, "raw/test_reg")
        path = storage.data_path("raw/test_reg")
        compute.register_table("test_reg", path)
        result = compute.execute("SELECT * FROM test_reg")
        assert len(result) == 2

    def test_collect(self, compute):
        df = pd.DataFrame({"x": [1, 2, 3]})
        records = compute.collect(df)
        assert len(records) == 3
        assert records[0]["x"] == 1


class TestExportContract:
    def test_export_file_parquet(self, storage):
        df = pd.DataFrame({"a": [1, 2, 3]})
        storage.write_parquet(df, "app/test_export")

        export = LocalExport(storage=storage)
        export_id = export.export_file("app/test_export", {
            "format": "parquet",
            "target": "file",
            "target_path": "exports/test",
        })
        assert export_id.startswith("exp_")

    def test_export_file_csv(self, storage):
        df = pd.DataFrame({"a": [1, 2, 3]})
        storage.write_parquet(df, "app/test_csv_export")

        export = LocalExport(storage=storage)
        export_id = export.export_file("app/test_csv_export", {
            "format": "csv",
            "target": "file",
            "target_path": "exports/csv_test",
        })
        assert export_id.startswith("exp_")

    def test_list_exports(self, storage):
        df = pd.DataFrame({"a": [1]})
        storage.write_parquet(df, "app/test_list")
        export = LocalExport(storage=storage)
        export.export_file("app/test_list", {"format": "parquet", "target_path": "exports/list_test"})
        exports = export.list_exports()
        assert len(exports) >= 1


class TestMetadataContract:
    def test_register_and_get_table(self, metadata):
        metadata.register_table("test_table", "raw", {"columns": {"id": "int"}}, "Test table")
        result = metadata.get_table("test_table")
        assert result is not None
        assert result["name"] == "test_table"
        assert result["zone"] == "raw"

    def test_list_tables(self, metadata):
        metadata.register_table("t1", "raw", {}, "")
        metadata.register_table("t2", "cleaned", {}, "")
        raw_tables = metadata.list_tables(zone="raw")
        assert len(raw_tables) >= 1
        all_tables = metadata.list_tables()
        assert len(all_tables) >= 2

    def test_lineage(self, metadata):
        metadata.add_lineage("stg_orders", "int_order_detail", "JOIN + decode")
        lineage = metadata.get_lineage("int_order_detail", "upstream")
        assert len(lineage) >= 1
        assert lineage[0]["source"] == "stg_orders"

    def test_quality_score(self, metadata):
        metadata.record_quality_result("test_table", "not_null", True)
        metadata.record_quality_result("test_table", "unique", False)
        score = metadata.get_quality_score("test_table")
        assert score["total_checks"] == 2
        assert score["passed"] == 1
        assert score["score"] == 0.5
