from db.models import IngestionRun
from db.session import SessionLocal


def main():
    db = SessionLocal()

    try:
        run = IngestionRun(
            source="manual_test",
            status="success",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        print(f"Inserted ingestion run with id={run.id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()