from pathlib import Path

import yaml

_config_cache: dict | None = None
_config_path = Path(__file__).parent.parent.parent / "config" / "profile.yaml"

_UNIMPLEMENTED_BACKENDS = {
    "storage": {"minio": "MinIOBackend", "s3": "S3Backend"},
    "compute": {"spark": "SparkEngine"},
    "query": {"trino": "TrinoEngine"},
    "export": {"s3": "S3Export"},
    "ingestion": {"airbyte": "AirbyteIngestion"},
    "metadata": {"postgresql": "PostgreSQLStore"},
}


def _raise_unimplemented(layer: str, backend: str):
    cls_name = _UNIMPLEMENTED_BACKENDS.get(layer, {}).get(backend, "Unknown")
    raise NotImplementedError(
        f"Backend '{backend}' ({cls_name}) is not yet implemented for layer '{layer}'. "
        f"Available backends for {layer}: see config/profile.yaml"
    )


def load_profile() -> dict:
    global _config_cache
    if _config_cache is None:
        with open(_config_path) as f:
            _config_cache = yaml.safe_load(f)
    return _config_cache


def reload_profile() -> dict:
    global _config_cache
    _config_cache = None
    return load_profile()


def get_storage():
    config = load_profile()
    backend = config["storage"]["backend"]
    if backend == "local_fs":
        from datamind.backends.storage.local_fs import LocalFSBackend
        return LocalFSBackend(root_path=config["storage"]["root_path"])
    if backend in _UNIMPLEMENTED_BACKENDS["storage"]:
        _raise_unimplemented("storage", backend)
    raise ValueError(f"Unknown storage backend: {backend}")


def get_compute():
    config = load_profile()
    backend = config["compute"]["backend"]
    if backend == "duckdb":
        from datamind.backends.compute.duckdb_engine import DuckDBEngine
        return DuckDBEngine()
    if backend in _UNIMPLEMENTED_BACKENDS["compute"]:
        _raise_unimplemented("compute", backend)
    raise ValueError(f"Unknown compute backend: {backend}")


def get_query():
    config = load_profile()
    backend = config["query"]["backend"]
    if backend == "duckdb":
        from datamind.backends.query.duckdb_engine import DuckDBQueryEngine
        return DuckDBQueryEngine()
    if backend in _UNIMPLEMENTED_BACKENDS["query"]:
        _raise_unimplemented("query", backend)
    raise ValueError(f"Unknown query backend: {backend}")


def get_export():
    config = load_profile()
    backend = config["export"]["backend"]
    if backend == "local":
        from datamind.backends.export.local_export import LocalExport
        return LocalExport(storage=get_storage())
    if backend in _UNIMPLEMENTED_BACKENDS["export"]:
        _raise_unimplemented("export", backend)
    raise ValueError(f"Unknown export backend: {backend}")


def get_ingestion():
    config = load_profile()
    backend = config["ingestion"]["backend"]
    if backend == "script":
        from datamind.backends.ingestion.python_script import PythonScriptIngestion
        return PythonScriptIngestion(storage=get_storage())
    if backend in _UNIMPLEMENTED_BACKENDS["ingestion"]:
        _raise_unimplemented("ingestion", backend)
    raise ValueError(f"Unknown ingestion backend: {backend}")


def get_metadata():
    config = load_profile()
    backend = config["metadata"]["backend"]
    if backend == "sqlite":
        from datamind.backends.metadata.sqlite_store import SQLiteStore
        root = config["storage"]["root_path"]
        return SQLiteStore(db_path=str(Path(root) / "metadata.db"))
    if backend in _UNIMPLEMENTED_BACKENDS["metadata"]:
        _raise_unimplemented("metadata", backend)
    raise ValueError(f"Unknown metadata backend: {backend}")


def get_observability():
    config = load_profile()
    log_backend = config["observability"]["log_backend"]
    if log_backend == "stdout":
        from datamind.backends.observability.stdout_obs import StdoutObservability
        return StdoutObservability()
    raise ValueError(f"Unknown observability log backend: {log_backend}")
