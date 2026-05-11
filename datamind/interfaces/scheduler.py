from abc import ABC, abstractmethod
from datetime import date


class SchedulerInterface(ABC):
    @abstractmethod
    def schedule(self, pipeline_def: dict) -> str:
        ...

    @abstractmethod
    def trigger(self, pipeline_id: str, params: dict | None = None) -> str:
        ...

    @abstractmethod
    def status(self, run_id: str) -> dict:
        ...

    @abstractmethod
    def backfill(self, pipeline_id: str, start: date, end: date) -> list[str]:
        ...
