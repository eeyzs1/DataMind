from abc import ABC, abstractmethod


class QueryInterface(ABC):
    @abstractmethod
    def execute(self, sql: str, params: dict | None = None) -> dict:
        ...

    @abstractmethod
    def natural_query(self, question: str, context: dict | None = None) -> dict:
        ...

    @abstractmethod
    def catalog(self, query: str | None = None) -> list[dict]:
        ...
