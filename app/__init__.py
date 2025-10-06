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
        db.create_all()  # pro čisté instalace

        # Bezpečná migrace staré tabulky users → doplnění chybějících sloupců
        try:
            with db.engine.begin() as conn:
                # 1) Vytvoř tabulku, pokud vůbec neexistuje
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(255),
                        name VARCHAR(255),
                        role VARCHAR(50) DEFAULT 'user',
                        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                    );
                """))

                # 2) Doplň chybějící sloupce (bez chyb při existenci)
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255);"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user';"))
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW();"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);"))

                # 3) Vyplň NULL hodnoty, aby šel sloupec uzamknout na NOT NULL
                conn.execute(text("UPDATE users SET password_hash = 'legacy-null' WHERE password_hash IS NULL;"))
                conn.execute(text("UPDATE users SET role = COALESCE(role, 'user');"))

                # 4) Teď teprve NOT NULL
                conn.execute(text("ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL;"))
                conn.execute(text("ALTER TABLE users ALTER COLUMN role SET NOT NULL;"))

                # 5) Ping
                conn.execute(text("SELECT 1;"))
        except Exception as e:
            print("DB bootstrap error:", e)
            raise


    return app
    # do create_app(), kde je route '/'
from flask import send_file

@app.get("/")
def root():
    root_index = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(root_index):
        return send_file(root_index)
    return app.send_static_file("index.html")

