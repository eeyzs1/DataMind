import os

import pandas as pd

from datamind.interfaces.storage import StorageInterface


class LocalFSBackend(StorageInterface):
    def __init__(self, root_path: str = "./data"):
        self.root_path = root_path

    def data_path(self, logical_path: str) -> str:
        path = os.path.join(self.root_path, logical_path)
        if not path.endswith(".parquet"):
            path = path + ".parquet"
        return path

    def read_parquet(self, path: str) -> pd.DataFrame:
        full_path = self.data_path(path)
        return pd.read_parquet(full_path)

    def write_parquet(self, df: pd.DataFrame, path: str, mode: str = "overwrite") -> None:
        full_path = self.data_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        if mode == "overwrite" and os.path.exists(full_path):
            os.remove(full_path)
        df.to_parquet(full_path, index=False)

    def exists(self, path: str) -> bool:
        full_path = self.data_path(path)
        return os.path.exists(full_path)

    def list_tables(self, zone: str) -> list[str]:
        zone_path = os.path.join(self.root_path, zone)
        if not os.path.exists(zone_path):
            return []
        tables = []
        for f in os.listdir(zone_path):
            if f.endswith(".parquet"):
                tables.append(f.replace(".parquet", ""))
        return sorted(tables)

    def get_size(self, path: str) -> int:
        full_path = self.data_path(path)
        if os.path.isfile(full_path):
            return os.path.getsize(full_path)
        return 0

    def delete(self, path: str) -> None:
        full_path = self.data_path(path)
        if os.path.isfile(full_path):
            os.remove(full_path)
