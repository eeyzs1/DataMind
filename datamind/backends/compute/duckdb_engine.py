import re
import threading

import duckdb
import pandas as pd

from datamind.interfaces.compute import ComputeInterface

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ALLOWED_OPS = {"=", "!=", "<>", "<", "<=", ">", ">=", "LIKE", "NOT LIKE", "IN", "NOT IN", "IS", "IS NOT"}
_PATH_WHITELIST = re.compile(r"^[A-Za-z0-9_./\\:-]+$")


class DuckDBEngine(ComputeInterface):
    def __init__(self):
        self._local = threading.local()
        self._closed = False

    @property
    def _conn(self):
        if self._closed:
            raise RuntimeError("DuckDBEngine is closed")
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = duckdb.connect()
        return self._local.conn

    @staticmethod
    def validate_identifier(name: str) -> str:
        if not _SAFE_IDENTIFIER.match(name):
            raise ValueError(f"Invalid SQL identifier: {name!r}")
        return name

    @staticmethod
    def validate_op(op: str) -> str:
        op_upper = op.strip().upper()
        if op_upper not in _ALLOWED_OPS:
            raise ValueError(f"Disallowed SQL operator: {op!r}")
        return op_upper

    @staticmethod
    def _validate_path(path: str) -> str:
        if not _PATH_WHITELIST.match(path):
            raise ValueError(f"Invalid file path in SQL context: {path!r}")
        return path

    def execute(self, sql: str, parameters: list | None = None) -> pd.DataFrame:
        if parameters:
            result = self._conn.execute(sql, parameters)
        else:
            result = self._conn.execute(sql)
        return result.df()

    def register_table(self, name: str, path: str) -> None:
        self.validate_identifier(name)
        self._validate_path(path)
        quoted_path = path.replace("'", "''")
        if path.endswith(".parquet") or "/" in path or "\\" in path:
            self._conn.execute(
                f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{quoted_path}')"
            )
        else:
            self._conn.execute(
                f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{quoted_path}/*.parquet')"
            )

    def collect(self, df: pd.DataFrame) -> list[dict]:
        return df.to_dict("records")

    def explain(self, sql: str) -> str:
        result = self._conn.execute(f"EXPLAIN {sql}")
        return str(result.fetchall())

    def close(self) -> None:
        self._closed = True
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
