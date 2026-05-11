import json
import os
import sqlite3
from datetime import datetime

from datamind.interfaces.metadata import MetadataInterface


class SQLiteStore(MetadataInterface):
    def __init__(self, db_path: str = "./data/metadata.db"):
        self._db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_db()

    def _init_db(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS tables (
                name TEXT PRIMARY KEY,
                zone TEXT NOT NULL,
                schema_json TEXT,
                description TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS lineage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                transformation TEXT DEFAULT '',
                created_at TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS quality_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                rule_json TEXT NOT NULL,
                created_at TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS quality_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                rule_name TEXT NOT NULL,
                passed INTEGER NOT NULL,
                detail_json TEXT,
                checked_at TEXT
            )
        """)
        self._conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def register_table(self, table_name: str, zone: str, schema: dict, description: str = "") -> None:
        now = datetime.now().isoformat()
        self._conn.execute("""
            INSERT OR REPLACE INTO tables (name, zone, schema_json, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (table_name, zone, json.dumps(schema), description, now, now))
        self._conn.commit()

    def get_table(self, table_name: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM tables WHERE name = ?", (table_name,)).fetchone()
        if row:
            return {"name": row[0], "zone": row[1], "schema": json.loads(row[2]), "description": row[3]}
        return None

    def list_tables(self, zone: str | None = None) -> list[dict]:
        if zone:
            rows = self._conn.execute("SELECT name, zone, description FROM tables WHERE zone = ?", (zone,)).fetchall()
        else:
            rows = self._conn.execute("SELECT name, zone, description FROM tables").fetchall()
        return [{"name": r[0], "zone": r[1], "description": r[2]} for r in rows]

    def add_lineage(self, source: str, target: str, transformation: str = "") -> None:
        now = datetime.now().isoformat()
        self._conn.execute("""
            INSERT INTO lineage (source, target, transformation, created_at)
            VALUES (?, ?, ?, ?)
        """, (source, target, transformation, now))
        self._conn.commit()

    def get_lineage(self, table_name: str, direction: str = "upstream", depth: int = 3) -> list[dict]:
        if direction == "upstream":
            rows = self._conn.execute(
                "SELECT source, target, transformation FROM lineage WHERE target = ?", (table_name,)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT source, target, transformation FROM lineage WHERE source = ?", (table_name,)
            ).fetchall()
        return [{"source": r[0], "target": r[1], "transformation": r[2]} for r in rows]

    def add_quality_rule(self, table_name: str, rule: dict) -> None:
        now = datetime.now().isoformat()
        self._conn.execute("""
            INSERT INTO quality_rules (table_name, rule_json, created_at)
            VALUES (?, ?, ?)
        """, (table_name, json.dumps(rule), now))
        self._conn.commit()

    def get_quality_rules(self, table_name: str | None = None) -> list[dict]:
        if table_name:
            rows = self._conn.execute(
                "SELECT id, table_name, rule_json FROM quality_rules WHERE table_name = ?",
                (table_name,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, table_name, rule_json FROM quality_rules"
            ).fetchall()
        return [{"id": r[0], "table_name": r[1], **json.loads(r[2])} for r in rows]

    def record_quality_result(self, table_name: str, rule_name: str, passed: bool, detail: dict | None = None) -> None:
        now = datetime.now().isoformat()
        self._conn.execute("""
            INSERT INTO quality_results (table_name, rule_name, passed, detail_json, checked_at)
            VALUES (?, ?, ?, ?, ?)
        """, (table_name, rule_name, 1 if passed else 0, json.dumps(detail or {}), now))
        self._conn.commit()

    def get_quality_score(self, table_name: str) -> dict:
        rows = self._conn.execute(
            "SELECT passed, COUNT(*) FROM quality_results WHERE table_name = ? GROUP BY passed",
            (table_name,)
        ).fetchall()
        total = sum(r[1] for r in rows)
        passed = sum(r[1] for r in rows if r[0] == 1)
        return {
            "table": table_name,
            "total_checks": total,
            "passed": passed,
            "score": passed / total if total > 0 else 1.0,
        }
