from abc import ABC, abstractmethod


class MetadataInterface(ABC):
    @abstractmethod
    def register_table(self, table_name: str, zone: str, schema: dict, description: str = "") -> None:
        ...

    @abstractmethod
    def get_table(self, table_name: str) -> dict | None:
        ...

    @abstractmethod
    def list_tables(self, zone: str | None = None) -> list[dict]:
        ...

    @abstractmethod
    def add_lineage(self, source: str, target: str, transformation: str = "") -> None:
        ...

    @abstractmethod
    def get_lineage(self, table_name: str, direction: str = "upstream", depth: int = 3) -> list[dict]:
        ...

    @abstractmethod
    def add_quality_rule(self, table_name: str, rule: dict) -> None:
        ...

    @abstractmethod
    def get_quality_rules(self, table_name: str | None = None) -> list[dict]:
        ...

    @abstractmethod
    def record_quality_result(self, table_name: str, rule_name: str, passed: bool, detail: dict | None = None) -> None:
        ...

    @abstractmethod
    def get_quality_score(self, table_name: str) -> dict:
        ...
