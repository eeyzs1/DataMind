from pathlib import Path

import yaml

_config_cache: dict | None = None
_config_path = Path(__file__).parent.parent.parent / "config" / "profile.yaml"


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
    elif backend == "minio":
        from datamind.backends.storage.minio_fs import MinIOBackend
        return MinIOBackend(
            endpoint=config["storage"]["endpoint"],
            access_key=config["storage"].get("access_key", ""),
            secret_key=config["storage"].get("secret_key", ""),
            bucket=config["storage"].get("bucket", "datamind"),
        )
    elif backend == "s3":
        from datamind.backends.storage.s3_fs import S3Backend
        return S3Backend(bucket=config["storage"]["bucket"])
    else:
        raise ValueError(f"Unknown storage backend: {backend}")


def get_compute():
    config = load_profile()
    backend = config["compute"]["backend"]
    if backend == "duckdb":
        from datamind.backends.compute.duckdb_engine import DuckDBEngine
        return DuckDBEngine()
    elif backend == "spark":
        from datamind.backends.compute.spark_engine import SparkEngine
        return SparkEngine(master=config["compute"]["master"])
    else:
        raise ValueError(f"Unknown compute backend: {backend}")


def get_query():
    config = load_profile()
    backend = config["query"]["backend"]
    if backend == "duckdb":
        from datamind.backends.compute.duckdb_engine import DuckDBEngine
        return DuckDBEngine()
    elif backend == "trino":
        from datamind.backends.query.trino_engine import TrinoEngine
        return TrinoEngine(
            host=config["query"]["host"],
            port=config["query"].get("port", 8080),
            catalog=config["query"].get("catalog", "iceberg"),
        )
    else:
        raise ValueError(f"Unknown query backend: {backend}")


def get_export():
    config = load_profile()
    backend = config["export"]["backend"]
    if backend == "local":
        from datamind.backends.export.local_export import LocalExport
        return LocalExport(storage=get_storage())
    elif backend == "s3":
        from datamind.backends.export.s3_export import S3Export
        return S3Export(storage=get_storage())
    else:
        raise ValueError(f"Unknown export backend: {backend}")


def get_ingestion():
    config = load_profile()
    backend = config["ingestion"]["backend"]
    if backend == "script":
        from datamind.backends.ingestion.python_script import PythonScriptIngestion
        return PythonScriptIngestion(storage=get_storage())
    elif backend == "airbyte":
        from datamind.backends.ingestion.airbyte_ingestion import AirbyteIngestion
        return AirbyteIngestion(
            host=config["ingestion"]["host"],
            port=config["ingestion"].get("port", 8001),
        )
    else:
        raise ValueError(f"Unknown ingestion backend: {backend}")


def get_metadata():
    config = load_profile()
    backend = config["metadata"]["backend"]
    if backend == "sqlite":
        from datamind.backends.metadata.sqlite_store import SQLiteStore
        root = config["storage"]["root_path"]
        return SQLiteStore(db_path=str(Path(root) / "metadata.db"))
    elif backend == "postgresql":
        from datamind.backends.metadata.postgresql_store import PostgreSQLStore
        return PostgreSQLStore(
            host=config["metadata"]["host"],
            port=config["metadata"].get("port", 5432),
            database=config["metadata"]["database"],
        )
    else:
        raise ValueError(f"Unknown metadata backend: {backend}")


def get_observability():
    config = load_profile()
    log_backend = config["observability"]["log_backend"]
    if log_backend == "stdout":
        from datamind.backends.observability.stdout_obs import StdoutObservability
        return StdoutObservability()
    else:
        from datamind.backends.observability.stdout_obs import StdoutObservability
        return StdoutObservability()
