import duckdb
import pandas as pd

from datamind.interfaces.compute import ComputeInterface


class DuckDBEngine(ComputeInterface):
    def __init__(self):
        self._conn = duckdb.connect()

    def execute(self, sql: str) -> pd.DataFrame:
        result = self._conn.execute(sql)
        return result.df()

    def register_table(self, name: str, path: str) -> None:
        if path.endswith(".parquet") or "/" in path or "\\" in path:
            self._conn.execute(
                f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{path}')"
            )
        else:
            self._conn.execute(
                f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{path}/*.parquet')"
            )

    def collect(self, df: pd.DataFrame) -> list[dict]:
        return df.to_dict("records")

    def explain(self, sql: str) -> str:
        result = self._conn.execute(f"EXPLAIN {sql}")
        return str(result.fetchall())

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __del__(self):
        self.close()
