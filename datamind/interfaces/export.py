from abc import ABC, abstractmethod


class ExportInterface(ABC):
    @abstractmethod
    def export_file(self, source_path: str, target_config: dict) -> str:
        ...

    @abstractmethod
    def export_api(self, source_path: str, target_config: dict) -> str:
        ...

    @abstractmethod
    def export_stream(self, source_path: str, topic: str) -> str:
        ...

    @abstractmethod
    def create_snapshot(self, source_path: str, snapshot_config: dict) -> str:
        ...

    @abstractmethod
    def list_exports(self, source_path: str | None = None) -> list[dict]:
        ...
