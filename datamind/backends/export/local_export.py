import os
import shutil
from datetime import datetime

from datamind.interfaces.export import ExportInterface


class LocalExport(ExportInterface):
    def __init__(self, storage):
        self._storage = storage
        self._export_log: list[dict] = []

    def export_file(self, source_path: str, target_config: dict) -> str:
        source_full = self._storage.data_path(source_path)
        target_dir = target_config.get("target_path", "exports")
        format_ = target_config.get("format", "parquet")

        export_dir = self._storage.data_path(target_dir)
        os.makedirs(export_dir, exist_ok=True)

        if os.path.isdir(source_full):
            for f in os.listdir(source_full):
                if f.endswith(".parquet"):
                    src = os.path.join(source_full, f)
                    if format_ == "csv":
                        import pandas as pd
                        df = pd.read_parquet(src)
                        csv_name = f.replace(".parquet", ".csv")
                        df.to_csv(os.path.join(export_dir, csv_name), index=False)
                    else:
                        shutil.copy2(src, os.path.join(export_dir, f))
        elif os.path.isfile(source_full):
            if format_ == "csv":
                import pandas as pd
                df = pd.read_parquet(source_full)
                csv_name = os.path.basename(source_full).replace(".parquet", ".csv")
                df.to_csv(os.path.join(export_dir, csv_name), index=False)
            else:
                shutil.copy2(source_full, os.path.join(export_dir, os.path.basename(source_full)))

        export_id = f"exp_{len(self._export_log) + 1}"
        self._export_log.append({
            "id": export_id,
            "source": source_path,
            "target": target_dir,
            "format": format_,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
        })
        return export_id

    def export_api(self, source_path: str, target_config: dict) -> str:
        import httpx

        df = self._storage.read_parquet(source_path)
        url = target_config["url"]
        records = df.to_dict("records")

        batch_size = target_config.get("batch_size", 1000)
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            httpx.post(url, json=batch, timeout=30.0)

        export_id = f"exp_api_{len(self._export_log) + 1}"
        self._export_log.append({
            "id": export_id,
            "source": source_path,
            "target": url,
            "format": "api",
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "rows": len(records),
        })
        return export_id

    def export_stream(self, source_path: str, topic: str) -> str:
        return f"exp_stream_noop_{topic}"

    def create_snapshot(self, source_path: str, snapshot_config: dict) -> str:
        source_full = self._storage.data_path(source_path)
        snapshot_dir = self._storage.data_path("snapshots")
        os.makedirs(snapshot_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"{os.path.basename(source_path)}_{ts}"
        target = os.path.join(snapshot_dir, snapshot_name)
        shutil.copytree(source_full, target) if os.path.isdir(source_full) else shutil.copy2(source_full, target)

        return target

    def list_exports(self, source_path: str | None = None) -> list[dict]:
        if source_path:
            return [e for e in self._export_log if e["source"] == source_path]
        return self._export_log
