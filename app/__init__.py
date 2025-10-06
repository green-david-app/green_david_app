import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    # --- cesty: static je v KOŘENI repa, ne uvnitř app/ ---
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    STATIC_DIR = os.path.join(BASE_DIR, "static")

    # explicitně nastavíme absolutní cestu ke statice
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key")

    database_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # registrace modelů/route
    from . import models  # noqa: F401
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # healthcheck
    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": "v17+psycopg3"}

    # kořenová stránka -> /static/index.html z KOŘENE repa
    @app.get("/")
    def root():
        return app.send_static_file("index.html")

    with app.app_context():
        db.create_all()

    return app
