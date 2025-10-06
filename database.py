import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Render sets DATABASE_URL. Locally we fall back to SQLite so you can run it without Postgres.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./local.db")

# IMPORTANT: switch SQLAlchemy to the psycopg3 driver if Postgres is used
# (fixes ImportError with psycopg2 on Python 3.13)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

class Base(DeclarativeBase):
    pass

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
