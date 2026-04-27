import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

database_url = os.environ.get("DATABASE_URL", "postgresql://fastapi_db_cske_user:SS5wPSC048wc8Z7nhvgAM0P8kLA1Vs5Z@dpg-d7n8dv8g4nts73b1ffa0-a/fastapi_db_cske")

if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is not set.")

# Normalize URL for psycopg3 driver
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
elif not database_url.startswith("postgresql+psycopg://"):
    database_url = "postgresql+psycopg://" + database_url.split("://", 1)[-1]

engine = create_engine(database_url, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()