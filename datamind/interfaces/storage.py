from abc import ABC, abstractmethod

import pandas as pd


class StorageInterface(ABC):
    @abstractmethod
    def read_parquet(self, path: str) -> pd.DataFrame:
        ...

    @abstractmethod
    def write_parquet(self, df: pd.DataFrame, path: str, mode: str = "overwrite") -> None:
        ...

    @abstractmethod
    def exists(self, path: str) -> bool:
        ...

    @abstractmethod
    def list_tables(self, zone: str) -> list[str]:
        ...

    @abstractmethod
    def get_size(self, path: str) -> int:
        ...

    @abstractmethod
    def delete(self, path: str) -> None:
        ...

    @abstractmethod
    def data_path(self, logical_path: str) -> str:
        ...

    def ensure_zone_dirs(self) -> None:
        for zone in ("raw", "cleaned", "detail", "summary", "app"):
            path = self.data_path(zone)
            self._ensure_dir(path)

    @staticmethod
    def _ensure_dir(path: str) -> None:
        import os
        os.makedirs(path, exist_ok=True)
