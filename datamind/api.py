import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from datamind.core.factory import (
    get_compute,
    get_export,
    get_ingestion,
    get_metadata,
    get_storage,
    load_profile,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("datamind.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    profile = load_profile()
    logger.info(f"DataMind API starting with profile: {profile['profile']}")
    yield
    logger.info("DataMind API shutting down")


app = FastAPI(title="DataMind API", version="0.1.0", lifespan=lifespan)


class BatchIngestRequest(BaseModel):
    source: str
    format: str = "csv"
    options: dict | None = None


class BatchExportRequest(BaseModel):
    source: str
    format: str = "parquet"
    target: str = "file"
    target_path: str | None = None
    filters: list[dict] | None = None


class QueryRequest(BaseModel):
    dataset: str
    dimensions: list[str] | None = None
    metrics: list[str] | None = None
    filters: list[dict] | None = None
    limit: int = 100


class NaturalQueryRequest(BaseModel):
    question: str


@app.get("/api/v1/health")
async def health():
    profile = load_profile()
    return {"status": "ok", "profile": profile["profile"]}


@app.post("/api/v1/ingest/batch")
async def ingest_batch(req: BatchIngestRequest):
    ingestion = get_ingestion()
    result = ingestion.ingest_batch({
        "name": req.source,
        "type": req.format,
        **(req.options or {}),
    })
    return {"ingestion_id": result, "status": "running"}


@app.post("/api/v1/export/batch")
async def export_batch(req: BatchExportRequest):
    export = get_export()
    target_config = {
        "format": req.format,
        "target": req.target,
        "target_path": req.target_path or f"exports/{req.source.split('/')[-1]}",
    }
    export_id = export.export_file(f"{req.source}", target_config)
    return {"export_id": export_id, "status": "completed"}


@app.get("/api/v1/export/{export_id}/status")
async def export_status(export_id: str):
    export = get_export()
    exports = export.list_exports()
    for e in exports:
        if e["id"] == export_id:
            return e
    raise HTTPException(status_code=404, detail="Export not found")


@app.get("/api/v1/catalog/tables")
async def list_tables(zone: str | None = None):
    storage = get_storage()
    if zone:
        return {"tables": storage.list_tables(zone)}
    result = {}
    for z in ("raw", "cleaned", "detail", "summary", "app"):
        tables = storage.list_tables(z)
        if tables:
            result[z] = tables
    return {"tables": result}


@app.get("/api/v1/catalog/search")
async def search_catalog(q: str = ""):
    storage = get_storage()
    results = []
    for zone in ("raw", "cleaned", "detail", "summary", "app"):
        for t in storage.list_tables(zone):
            if q.lower() in t.lower():
                results.append({"name": t, "zone": zone})
    return {"results": results}


@app.get("/api/v1/lineage/{table_name}")
async def get_lineage(table_name: str, direction: str = "upstream", depth: int = 3):
    metadata = get_metadata()
    lineage = metadata.get_lineage(table_name, direction, depth)
    return {"table": table_name, "direction": direction, "lineage": lineage}


@app.get("/api/v1/quality/{table_name}/score")
async def quality_score(table_name: str):
    metadata = get_metadata()
    return metadata.get_quality_score(table_name)


@app.post("/api/v1/query")
async def query_data(req: QueryRequest):
    compute = get_compute()
    storage = get_storage()

    if not storage.exists(req.dataset):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {req.dataset}")

    table_path = storage.data_path(req.dataset)
    table_name = req.dataset.replace("/", "_").replace("-", "_")
    compute.validate_identifier(table_name)
    compute.register_table(table_name, table_path)

    select_parts = []
    if req.dimensions:
        for d in req.dimensions:
            compute.validate_identifier(d)
            select_parts.append(d)
    if req.metrics:
        for m in req.metrics:
            compute.validate_identifier(m)
            select_parts.append(m)
    if not select_parts:
        select_parts = ["*"]

    sql = f"SELECT {', '.join(select_parts)} FROM {table_name}"
    params: list = []

    if req.filters:
        conditions = []
        for f in req.filters:
            compute.validate_identifier(f["field"])
            op = compute.validate_op(f["op"])
            conditions.append(f"{f['field']} {op} ?")
            params.append(f["value"])
        sql += " WHERE " + " AND ".join(conditions)

    if req.dimensions and req.metrics:
        sql += f" GROUP BY {', '.join(req.dimensions)}"

    limit = max(1, min(req.limit, 10000))
    sql += f" LIMIT {limit}"

    try:
        df = compute.execute(sql, params if params else None)
        return {"data": df.to_dict("records"), "row_count": len(df), "sql": sql}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/query/natural")
async def natural_query(req: NaturalQueryRequest):
    from datamind.core.natural_query import TemplateMatcher
    matcher = TemplateMatcher()
    result = matcher.match(req.question)
    if result:
        compute = get_compute()
        storage = get_storage()
        table_name = result.get("table", "app_daily_revenue")
        zone = "app" if table_name.startswith("app_") else "summary"
        compute.register_table(table_name, storage.data_path(f"{zone}/{table_name}"))
        try:
            df = compute.execute(result["sql"])
            return {
                "question": req.question,
                "sql": result["sql"],
                "chart_type": result["chart"],
                "data": df.to_dict("records"),
            }
        except Exception as e:
            return {"question": req.question, "error": str(e)}
    return {"question": req.question, "error": "No matching template found"}
