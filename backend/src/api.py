"""Read-only FastAPI for the generated OEE dataset."""
import csv
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="YottaFlex OEE API", version="1.0")
DATA_DIR = Path(__file__).resolve().parents[1] / "outputs" / "full"
def read_csv(table):
    path = DATA_DIR / f"{table}.csv"
    if not path.exists():
        raise HTTPException(404, "Dataset missing. Run generator first.")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

@app.get("/health")
def health():
    return {"status": "ok", "dataset_ready": (DATA_DIR / "manifest.json").exists()}

@app.get("/summary")
def summary():
    aggregates = read_csv("oee_aggregate")
    machines = read_csv("machine")
    issues = read_csv("ground_truth")
    oees = [float(r["oee"]) for r in aggregates]
    return {"machines": len(machines), "machine_shifts": len(aggregates), "anomalies": len(issues), "average_oee": round(sum(oees) / len(oees), 4) if oees else 0}

@app.get("/machines")
def machines():
    return read_csv("machine")

@app.get("/oee")
def oee(machine_id: str | None = Query(default=None)):
    rows = read_csv("oee_aggregate")
    return [r for r in rows if not machine_id or r["machine_id"] == machine_id]

@app.get("/anomalies")
def anomalies():
    return read_csv("ground_truth")

@app.get("/manifest")
def manifest():
    path = DATA_DIR / "manifest.json"
    if not path.exists():
        raise HTTPException(404, "Dataset missing. Run generator first.")
    return json.loads(path.read_text(encoding="utf-8"))
