from datamind.backends.compute.duckdb_engine import DuckDBEngine
from datamind.interfaces.query import QueryInterface


class DuckDBQueryEngine(QueryInterface):
    def __init__(self):
        self._engine = DuckDBEngine()

    def execute(self, sql: str, params: dict | None = None) -> dict:
        parameters = list(params.values()) if params else None
        df = self._engine.execute(sql, parameters)
        return {"data": df.to_dict("records"), "row_count": len(df), "sql": sql}

    def natural_query(self, question: str, context: dict | None = None) -> dict:
        from datamind.core.natural_query import TemplateMatcher
        matcher = TemplateMatcher()
        result = matcher.match(question)
        if result:
            return {"sql": result["sql"], "chart_type": result["chart"], "table": result["table"]}
        return {"error": "No matching template found", "question": question}

    def catalog(self, query: str | None = None) -> list[dict]:
        return []

    def close(self) -> None:
        self._engine.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
