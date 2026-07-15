import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("RMIP_DSS_DB_PATH", BASE_DIR / "database" / "rmip_dss.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    seed_data()


def seed_data() -> None:
    from .models import MarketInsight, PricingRun

    db = SessionLocal()
    try:
        if not db.query(PricingRun).first():
            db.add(
                PricingRun(
                    treaty_id="TRT-001",
                    client_name="Example Reinsurer",
                    technical_premium=125000.0,
                    commercial_premium=150000.0,
                )
            )

        if not db.query(MarketInsight).first():
            db.add(
                MarketInsight(
                    region="North America",
                    line_of_business="Property Catastrophe",
                    summary="Example market insight seeded for early demos.",
                    sentiment_score=0.72,
                )
            )

        db.commit()
    finally:
        db.close()
