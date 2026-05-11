from abc import ABC, abstractmethod

import pandas as pd


class ComputeInterface(ABC):
    @abstractmethod
    def execute(self, sql: str) -> pd.DataFrame:
        ...

    @abstractmethod
    def register_table(self, name: str, path: str) -> None:
        ...

    @abstractmethod
    def collect(self, df: pd.DataFrame) -> list[dict]:
        ...

    @abstractmethod
    def explain(self, sql: str) -> str:
        ...

    @abstractmethod
    def close(self) -> None:
        ...
