from abc import ABC, abstractmethod


class IngestionInterface(ABC):
    @abstractmethod
    def ingest_batch(self, source_config: dict) -> str:
        ...

    @abstractmethod
    def ingest_stream(self, source_config: dict) -> str:
        ...

    @abstractmethod
    def list_sources(self) -> list[dict]:
        ...

    @abstractmethod
    def get_status(self, ingestion_id: str) -> dict:
        ...
