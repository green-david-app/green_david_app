import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()

def create_app():
    # STATIC je v KOŘENI repa
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    STATIC_DIR = os.path.join(BASE_DIR, "static")

    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key")

    # DB URL → psycopg3 + SSL
    database_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql+psycopg://") and "sslmode=" not in database_url:
        sep = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{sep}sslmode=require"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # MODELY + ROUTY
    from . import models  # noqa: F401
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # HEALTHCHECK
    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": "v17+psycopg3"}

    # KOŘEN → /static/index.html
    @app.get("/")
    def root():
        return app.send_static_file("index.html")

    # Lehký bootstrap DB (tabulky pro čisté instalace)
    with app.app_context():
        db.create_all()
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as e:
            print("DB connectivity error:", e)
            raise

    return app
