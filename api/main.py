from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.deps import get_db
from db.models import IngestionRun
from db.session import engine

app = FastAPI(title="NasaHub API")


@app.get("/health")
def health():
    db_ok = False

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
    }


@app.get("/ingestion-runs")
def list_ingestion_runs(db: Session = Depends(get_db)):
    runs = db.query(IngestionRun).order_by(IngestionRun.id.desc()).all()

    return [
        {
            "id": run.id,
            "source": run.source,
            "status": run.status,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
        }
        for run in runs
    ]