import os
from datetime import datetime

import pandas as pd

from datamind.interfaces.ingestion import IngestionInterface


class PythonScriptIngestion(IngestionInterface):
    def __init__(self, storage):
        self._storage = storage
        self._ingestion_log: list[dict] = []

    def ingest_batch(self, source_config: dict) -> str:
        source_type = source_config.get("type", "csv")
        source_name = source_config["name"]
        url = source_config.get("url", "")

        self._storage.ensure_zone_dirs()

        if source_type == "csv":
            df = self._read_csv(url, source_config)
        elif source_type == "parquet":
            df = pd.read_parquet(url)
        elif source_type == "api":
            import httpx
            resp = httpx.get(url, timeout=60.0)
            data = resp.json()
            df = pd.DataFrame(data if isinstance(data, list) else data.get("data", []))
        elif source_type == "local_csv":
            df = pd.read_csv(url)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        df["_ingested_at"] = datetime.now()
        df["_source"] = source_name
        df["_batch_id"] = f"batch_{len(self._ingestion_log) + 1}"

        output_path = f"raw/{source_name}"
        self._storage.write_parquet(df, output_path)

        ingestion_id = f"ing_{len(self._ingestion_log) + 1}"
        self._ingestion_log.append({
            "id": ingestion_id,
            "source": source_name,
            "rows": len(df),
            "size_bytes": self._storage.get_size(output_path),
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
        })
        return ingestion_id

    def ingest_stream(self, source_config: dict) -> str:
        return "ing_stream_noop"

    def list_sources(self) -> list[dict]:
        return self._ingestion_log

    def get_status(self, ingestion_id: str) -> dict:
        for entry in self._ingestion_log:
            if entry["id"] == ingestion_id:
                return entry
        return {"id": ingestion_id, "status": "not_found"}

    def _read_csv(self, url: str, config: dict) -> pd.DataFrame:
        local_path = self._resolve_local_path(url, config)
        if local_path and os.path.exists(local_path):
            return pd.read_csv(local_path, encoding=config.get("encoding", "utf-8"))

        if url.startswith("http"):
            import httpx
            resp = httpx.get(url, timeout=120.0, follow_redirects=True)
            resp.raise_for_status()
            from io import StringIO
            return pd.read_csv(StringIO(resp.text), encoding=config.get("encoding", "utf-8"))

        raise FileNotFoundError(f"Cannot resolve data source: {url}")

    def _resolve_local_path(self, url: str, config: dict) -> str | None:
        data_dir = self._storage.data_path("raw")
        name = config.get("name", "")
        for ext in (".csv", ".parquet"):
            candidate = os.path.join(data_dir, f"{name}{ext}")
            if os.path.exists(candidate):
                return candidate
        return None
