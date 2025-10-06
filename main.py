
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
import os

app = Flask(__name__)
# ⚠️ change this in production
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

# --- Database setup (SQLite in /data/app.db) ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "app.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def normalize_email(email: str) -> str:
        return (email or "").strip().lower()

    @staticmethod
    def normalize_username(username: str) -> str:
        return (username or "").strip()

with app.app_context():
    db.create_all()

# --- Helpers ---
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)

# --- Routes ---
@app.route("/")
def index():
    user = current_user()
    if user:
        return render_template("index.html", user=user)
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = User.normalize_username(request.form.get("username"))
        email = User.normalize_email(request.form.get("email"))
        password = request.form.get("password")

        # Basic validation
        if not username or not email or not password:
            flash("Vyplň uživatelské jméno, e‑mail a heslo.", "error")
            return redirect(url_for("register"))

        # Pre-check to give friendly error (avoids raw IntegrityError)
        collision = User.query.filter((User.username == username) | (User.email == email)).first()
        if collision:
            if collision.username == username and collision.email == email:
                flash("Uživatel s tímto jménem i e‑mailem už existuje.", "error")
            elif collision.username == username:
                flash("Uživatel s tímto jménem už existuje.", "error")
            else:
                flash("Uživatel s tímto e‑mailem už existuje.", "error")
            return redirect(url_for("register"))

        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Účet byl úspěšně vytvořen. Přihlas se.", "success")
            return redirect(url_for("login"))
        except IntegrityError:
            db.session.rollback()
            # Fallback – kdyby došlo ke kolizi mezi pre-checkem a commitem (race condition)
            flash("Uživatel s tímto e‑mailem nebo jménem už existuje.", "error")
            return redirect(url_for("register"))
        except Exception as e:
            db.session.rollback()
            flash(f"Nepodařilo se vytvořit účet: {e}", "error")
            return redirect(url_for("register"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = User.normalize_email(request.form.get("email"))
        password = request.form.get("password")

        if not email or not password:
            flash("Zadej e‑mail i heslo.", "error")
            return redirect(url_for("login"))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            flash("Přihlášení úspěšné.", "success")
            return redirect(url_for("index"))
        flash("Neplatný e‑mail nebo heslo.", "error")
        return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Byl jsi odhlášen.", "info")
    return redirect(url_for("login"))

# --- Ensure upload directory exists (if used elsewhere) ---
os.makedirs(os.path.join(BASE_DIR, "static", "uploads"), exist_ok=True)

# Minimal fallback templates if not provided (optional safeguard)
# These help avoid 500 errors if templates are missing in your repo.
# Remove if you already have your own templates.
@app.context_processor
def inject_defaults():
    return dict(app_name="green_david_app")

@app.route("/_fallback_template/<name>")
def _fallback_template(name):
    # Not meant for production; only a debug helper.
    return f"<h1>{name}</h1>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
