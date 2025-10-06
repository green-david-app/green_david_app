import os
from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # --- základní konfigurace ---
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key")

    database_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
    # psycopg3 driver
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # --- registrace modelů a blueprintů ---
    from . import models  # noqa: F401
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # --- HEALTHCHECK pro Render ---
    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": "v17+psycopg3"}

    # --- KOŘENOVÁ STRÁNKA: vrátí statický index.html (UI) ---
    @app.get("/")
    def root():
        return send_from_directory("static", "index.html")

    # případně: /static/* obsluhuje Flask sám podle složky "static/"

    # --- bootstrap DB (jednoduché vytvoření tabulek) ---
    with app.app_context():
        db.create_all()

    return app
