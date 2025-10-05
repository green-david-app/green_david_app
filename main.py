import os
import sqlite3
from datetime import datetime
from flask import Flask, send_from_directory, request, jsonify, session, g
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.environ.get("DB_PATH", "app.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-" + os.urandom(16).hex())

# Serve static files directly from repo root (no /static folder)
app = Flask(__name__, static_folder=".", static_url_path="")
app.secret_key = SECRET_KEY

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    c = db.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','manager','worker')),
            password_hash TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    db.commit()
    # seed default admin if not exists
    c.execute("SELECT COUNT(*) as c FROM users")
    count = c.fetchone()["c"]
    if count == 0:
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@greendavid.local")
        admin_name = os.environ.get("ADMIN_NAME", "Admin")
        admin_pwd = os.environ.get("ADMIN_PASSWORD", "admin123")
        c.execute("""INSERT INTO users(email,name,role,password_hash,active,created_at)
                     VALUES (?,?,?,?,1,?)""",
                  (admin_email, admin_name, "admin",
                   generate_password_hash(admin_pwd),
                   datetime.utcnow().isoformat()))
        db.commit()

@app.before_request
def ensure_db():
    init_db()

# -------- Routes --------
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/health")
def health():
    return {"status": "ok"}

# -------- Helpers --------
def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    db = get_db()
    row = db.execute("SELECT id,email,name,role,active FROM users WHERE id=?",(uid,)).fetchone()
    if not row:
        return None
    return dict(row)

def require_auth():
    u = current_user()
    if not u or not u.get("active"):
        return None, (jsonify({"ok": False, "error": "unauthorized"}), 401)
    return u, None

def require_admin():
    u, err = require_auth()
    if err: return None, err
    if u["role"] != "admin":
        return None, (jsonify({"ok": False, "error": "forbidden"}), 403)
    return u, None

# -------- API: auth --------
@app.route("/api/me", methods=["GET"])
def api_me():
    u = current_user()
    if not u:
        return jsonify({"ok": True, "authenticated": False})
    return jsonify({"ok": True, "authenticated": True, "user": u})

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    db = get_db()
    row = db.execute("SELECT id,email,name,role,password_hash,active FROM users WHERE email=?", (email,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], password) or not row["active"]:
        return jsonify({"ok": False, "error": "invalid_credentials"}), 401
    session["uid"] = row["id"]
    return jsonify({"ok": True})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("uid", None)
    return jsonify({"ok": True})

# -------- API: users (admin only) --------
@app.route("/api/users", methods=["GET","POST","PATCH"])
def api_users():
    admin, err = require_admin()
    if err: return err
    db = get_db()
    if request.method == "GET":
        rows = db.execute("SELECT id,email,name,role,active,created_at FROM users ORDER BY id ASC").fetchall()
        return jsonify({"ok": True, "users":[dict(r) for r in rows]})
    data = request.get_json(force=True, silent=True) or {}
    if request.method == "POST":
        email = (data.get("email") or "").strip().lower()
        name = data.get("name") or ""
        role = data.get("role") or "worker"
        pwd  = data.get("password") or ""
        if not (email and name and pwd and role in ("admin","manager","worker")):
            return jsonify({"ok": False, "error":"invalid_input"}), 400
        try:
            db.execute("""INSERT INTO users(email,name,role,password_hash,active,created_at)
                          VALUES (?,?,?,?,1,?)""",
                       (email, name, role, generate_password_hash(pwd), datetime.utcnow().isoformat()))
            db.commit()
            return jsonify({"ok": True})
        except sqlite3.IntegrityError:
            return jsonify({"ok": False, "error":"email_exists"}), 400
    if request.method == "PATCH":
        uid = data.get("id")
        updates = []
        params = []
        if "role" in data:
            if data["role"] not in ("admin","manager","worker"):
                return jsonify({"ok": False, "error":"bad_role"}), 400
            updates.append("role=?"); params.append(data["role"])
        if "active" in data:
            updates.append("active=?"); params.append(1 if data["active"] else 0)
        if "password" in data and data["password"]:
            updates.append("password_hash=?"); params.append(generate_password_hash(data["password"]))
        if not uid or not updates:
            return jsonify({"ok": False, "error":"invalid_input"}), 400
        params.append(uid)
        db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)
        db.commit()
        return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
