import os

import pandas as pd
import pytest

from datamind.backends.compute.duckdb_engine import DuckDBEngine
from datamind.backends.export.local_export import LocalExport
from datamind.backends.metadata.sqlite_store import SQLiteStore
from datamind.backends.storage.local_fs import LocalFSBackend


@pytest.fixture
def workspace(tmp_path):
    root = str(tmp_path / "data")
    storage = LocalFSBackend(root_path=root)
    storage.ensure_zone_dirs()
    return {
        "storage": storage,
        "root": root,
        "tmp": tmp_path,
    }


class TestE2EIngestToExport:
    def test_full_pipeline(self, workspace):
        storage = workspace["storage"]

        df = pd.DataFrame({
            "order_id": ["O001", "O002", "O003"],
            "customer_id": ["C001", "C002", "C001"],
            "amount": [100.0, 200.0, 150.0],
            "order_time": ["2024-01-15", "2024-01-16", "2024-01-17"],
        })
        storage.write_parquet(df, "raw/test_orders")

        assert storage.exists("raw/test_orders")
        raw_df = storage.read_parquet("raw/test_orders")
        assert len(raw_df) == 3

        compute = DuckDBEngine()
        raw_path = storage.data_path("raw/test_orders")
        compute.register_table("raw_orders", raw_path)

        cleaned_df = compute.execute("""
            SELECT
                order_id,
                customer_id,
                amount,
                order_time::DATE AS order_date
            FROM raw_orders
            WHERE order_id IS NOT NULL
        """)
        storage.write_parquet(cleaned_df, "cleaned/stg_test_orders")
        assert storage.exists("cleaned/stg_test_orders")

        compute.register_table("stg_orders", storage.data_path("cleaned/stg_test_orders"))
        summary_df = compute.execute("""
            SELECT
                order_date,
                COUNT(*) AS order_count,
                SUM(amount) AS total_revenue
            FROM stg_orders
            GROUP BY order_date
            ORDER BY order_date
        """)
        storage.write_parquet(summary_df, "summary/fct_test_revenue")
        assert storage.exists("summary/fct_test_revenue")

        export = LocalExport(storage=storage)
        export_id = export.export_file("summary/fct_test_revenue", {
            "format": "parquet",
            "target": "file",
            "target_path": "exports/test_revenue",
        })
        assert export_id.startswith("exp_")

        csv_export_id = export.export_file("summary/fct_test_revenue", {
            "format": "csv",
            "target": "file",
            "target_path": "exports/test_revenue_csv",
        })
        assert csv_export_id.startswith("exp_")

        exports = export.list_exports()
        assert len(exports) == 2

        compute.close()

    def test_metadata_tracking(self, workspace):
        storage = workspace["storage"]
        metadata = SQLiteStore(db_path=os.path.join(workspace["root"], "metadata.db"))

        df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
        storage.write_parquet(df, "raw/test_meta")

        metadata.register_table("test_meta", "raw", {"columns": {"id": "int", "name": "str"}}, "Test table")
        metadata.add_lineage("raw_source", "test_meta", "ingestion")
        metadata.record_quality_result("test_meta", "not_null", True)
        metadata.record_quality_result("test_meta", "unique", True)

        table = metadata.get_table("test_meta")
        assert table is not None
        assert table["zone"] == "raw"

        lineage = metadata.get_lineage("test_meta", "upstream")
        assert len(lineage) == 1

        score = metadata.get_quality_score("test_meta")
        assert score["score"] == 1.0

        metadata.close()
