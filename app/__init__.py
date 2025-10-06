import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key")

    # Render typicky dává DATABASE_URL ve tvaru postgres:// nebo postgresql://
    database_url = os.getenv("DATABASE_URL", "sqlite:///local.db")

    # SQLAlchemy s psycopg3 používá schéma 'postgresql+psycopg://'
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Registrace modelů a blueprintů
    from . import models  # noqa: F401
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # Healthcheck
    @app.get("/")
    def index():
        return {"status": "ok", "version": "v17+psycopg3"}

    # Založení tabulek při startu (rychlá bootstrap varianta)
    with app.app_context():
        db.create_all()

    return app
