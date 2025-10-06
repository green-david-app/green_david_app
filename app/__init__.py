import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key")
    database_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    from .models import User
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    with app.app_context():
        db.create_all()

    return app

