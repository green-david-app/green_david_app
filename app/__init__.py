import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()

def create_app():
    # static je v KOŘENI repa
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    STATIC_DIR = os.path.join(BASE_DIR, "static")

    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key")

    # --- DB URL + psycopg3 + SSL ---
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

    # ---------- MODELY & ROUTY ----------
    from . import models  # noqa: F401
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # ---------- HEALTH ----------
    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": "v17+psycopg3"}

    # ---------- ROOT → statický index ----------
    @app.get("/")
    def root():
        return app.send_static_file("index.html")

    # ---------- BOOTSTRAP DB ----------
    with app.app_context():
        db.create_all()  # pro nové instalace

        # ✳️ Doplň chybějící sloupce do staré tabulky users (bez nutnosti ruční migrace)
        try:
            with db.engine.begin() as conn:
                # vytvoř tabulku pokud vůbec neexistuje
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        name VARCHAR(255),
                        role VARCHAR(50) NOT NULL DEFAULT 'user',
                        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                    );
                """))
                # doplň chybějící sloupce (bez rozbití existujících)
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);"))
                conn.execute(text("ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL;"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255);"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) NOT NULL DEFAULT 'user';"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW();"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);"))
                # drobný ping, ať hned víme, že připojení funguje
                conn.execute(text("SELECT 1;"))
        except Exception as e:
            print("DB bootstrap error:", e)
            raise

    return app
