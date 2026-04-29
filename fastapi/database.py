import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Prefer explicit DATABASE_URL; fall back to a local SQLite file for
# quick local testing when no DATABASE_URL is provided.
database_url = os.environ.get("DATABASE_URL") or "sqlite:///./local_dev.db"

# Normalize Postgres URLs to use the psycopg driver when a remote
# DATABASE_URL is provided.
if database_url and (database_url.startswith("postgres://") or database_url.startswith("postgresql://")):
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

# For SQLite on local dev, allow the check_same_thread arg required by
# SQLAlchemy when using the same connection in multiple threads.
if database_url.startswith("sqlite://"):
    engine = create_engine(database_url, connect_args={"check_same_thread": False}, echo=True)
else:
    engine = create_engine(database_url, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()