import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()

def create_app():
    # static/ je v kořeni repa
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

    # Render Postgres obvykle vyžaduje SSL. Pokud není v URL, přilepíme ho.
    if database_url.startswith("postgresql+psycopg://") and "sslmode=" not in database_url:
        sep = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{sep}sslmode=require"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # modely + blueprinty
    from . import models  # noqa: F401
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # healthz (základní)
    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": "v17+psycopg3"}

    # root -> statický index
    @app.get("/")
    def root():
        return app.send_static_file("index.html")

    # první bootstrap tabulek + ověření DB připojení
    with app.app_context():
        db.create_all()
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as e:
            # selže-li připojení (např. kvůli SSL), uvidíš to v Render logs
            print("DB connectivity error:", e)
            raise

    return app
