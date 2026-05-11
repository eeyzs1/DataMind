from abc import ABC, abstractmethod


class ObservabilityInterface(ABC):
    @abstractmethod
    def log(self, level: str, message: str, context: dict | None = None) -> None:
        ...

    @abstractmethod
    def metric(self, name: str, value: float, tags: dict | None = None) -> None:
        ...

    @abstractmethod
    def trace(self, span_name: str, parent_id: str | None = None) -> str:
        ...

    @abstractmethod
    def alert(self, severity: str, title: str, detail: str) -> None:
        ...
