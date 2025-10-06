import os
from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

Base = declarative_base()

def _make_database_url() -> str:
    # Prefer DATABASE_URL (Render/Heroku style), fallback to SQLite file
    url = os.getenv("DATABASE_URL")
    if url:
        # Render sometimes provides a postgres URL without driver
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        return url
    # default to sqlite file
    return "sqlite:///app.db"

def get_engine(echo: bool = False):
    url = _make_database_url()
    if url.startswith("sqlite"):
        # needed for SQLite with Flask in multi-thread envs
        engine = create_engine(url, echo=echo, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(url, echo=echo, pool_pre_ping=True)
    return engine

def init_db(app=None, echo: bool = False):
    engine = get_engine(echo=echo)
    Base.metadata.create_all(engine)
    # scoped session so it's thread-safe
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Session = scoped_session(session_factory)
    if app:
        @app.teardown_appcontext
        def remove_session(exception=None):
            Session.remove()
    return Session
