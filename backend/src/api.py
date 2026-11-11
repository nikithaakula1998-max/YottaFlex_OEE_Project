
"""Read-only FastAPI for the YottaFlex manufacturing OEE dataset."""

import csv
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

app = FastAPI(
    title="YottaFlex OEE API",
    description="Manufacturing OEE analytics backed by SQLite.",
    version="2.0",
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "outputs" / "full"
DB_PATH = DATA_DIR / "oee.sqlite"


def get_connection():
    """Open the existing SQLite database in read-only mode."""
    if not DB_PATH.is_file():
        raise HTTPException(
            status_code=503,
            detail="SQLite database missing. Run the database loader first.",
        )

    try:
        connection = sqlite3.connect(
            DB_PATH.as_uri() + "?mode=ro",
            uri=True,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        return connection
    except sqlite3.Error as error:
        raise HTTPException(
            status_code=503,
            detail="Unable to open the SQLite database.",
        ) from error


def query_database(sql, parameters=()):
    """Execute a read-only query and return JSON-compatible records."""
    try:
        with closing(get_connection()) as connection:
            cursor = connection.execute(sql, parameters)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        raise HTTPException(
            status_code=500,
            detail="Database query failed.",
        ) from error


def read_csv(table):
    """Read auxiliary CSV data, such as anomaly ground truth."""
    allowed_tables = {"ground_truth"}

    if table not in allowed_tables:
        raise HTTPException(
            status_code=400,
            detail="Unsupported CSV table.",
        )

    path = DATA_DIR / f"{table}.csv"

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"{table}.csv is missing.",
        )

    try:
        with path.open(newline="", encoding="utf-8-sig") as file:
            return list(csv.DictReader(file))
    except (OSError, csv.Error) as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to read anomaly data.",
        ) from error


@app.get("/health")
def health():
    """Report API and dataset readiness."""
    database_ready = False

    if DB_PATH.is_file():
        try:
            with closing(get_connection()) as connection:
                connection.execute("SELECT 1 FROM machine LIMIT 1")
                connection.execute(
                    "SELECT 1 FROM oee_aggregate LIMIT 1"
                )
                database_ready = True
        except (HTTPException, sqlite3.Error):
            database_ready = False

    return {
        "status": "ok" if database_ready else "degraded",
        "dataset_ready": database_ready,
        "database": "sqlite",
        "manifest_ready": (DATA_DIR / "manifest.json").is_file(),
    }


@app.get("/summary")
def summary():
    """Return manufacturing summary metrics."""
    rows = query_database(
        """
        SELECT
            (SELECT COUNT(*) FROM machine) AS machines,
            COUNT(*) AS machine_shifts,
            COALESCE(AVG(oee), 0) AS average_oee
        FROM oee_aggregate
        """
    )

    result = rows[0]
    anomalies = read_csv("ground_truth")

    return {
        "machines": result["machines"],
        "machine_shifts": result["machine_shifts"],
        "anomalies": len(anomalies),
        "labelled_anomalies": len(anomalies),
        "average_oee": round(result["average_oee"], 4),
    }


@app.get("/machines")
def machines():
    """Return machine master data."""
    return query_database(
        """
        SELECT machine_id, line_id, name, status
        FROM machine
        ORDER BY machine_id
        """
    )


@app.get("/oee")
def oee(
    machine_id: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
):
    """Return OEE aggregates with optional filtering and pagination."""
    sql = """
        SELECT *
        FROM oee_aggregate
    """

    parameters = []

    if machine_id:
        sql += " WHERE machine_id = ?"
        parameters.append(machine_id)

    sql += " ORDER BY machine_id, shift_id, aggregate_id"

    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        parameters.extend([limit, offset])
    elif offset:
        sql += " LIMIT -1 OFFSET ?"
        parameters.append(offset)

    return query_database(sql, tuple(parameters))


@app.get("/anomalies")
def anomalies():
    """Return labelled anomalies from the generator."""
    return read_csv("ground_truth")


@app.get("/manifest")
def manifest():
    """Return the reproducibility manifest."""
    path = DATA_DIR / "manifest.json"

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Generation manifest is missing.",
        )

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to read the generation manifest.",
        ) from error
