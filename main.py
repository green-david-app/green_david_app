import os
import sqlite3
from datetime import datetime
from flask import Flask, send_from_directory, request, jsonify, session, g
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.environ.get("DB_PATH", "app.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-" + os.urandom(16).hex())

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
    # Users
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
    # Jobs
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            client TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Plán',
            city TEXT NOT NULL,
            code TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)
    # Employees
    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    # Warehouse items
    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site TEXT NOT NULL CHECK(site IN ('lipnik','praha')),
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            qty REAL NOT NULL DEFAULT 0,
            unit TEXT NOT NULL
        )
    """)
    db.commit()

    # seed default admin
    cur = db.execute("SELECT COUNT(*) as c FROM users")
    if cur.fetchone()["c"] == 0:
        db.execute("""INSERT INTO users(email,name,role,password_hash,active,created_at)
                      VALUES (?,?,?,?,1,?)""",
                   (os.environ.get("ADMIN_EMAIL","admin@greendavid.local"),
                    os.environ.get("ADMIN_NAME","Admin"),
                    "admin",
                    generate_password_hash(os.environ.get("ADMIN_PASSWORD","admin123")),
                    datetime.utcnow().isoformat()))
        db.commit()

@app.before_request
def ensure_db():
    init_db()

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/health")
def health():
    return {"status": "ok"}

def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    db = get_db()
    row = db.execute("SELECT id,email,name,role,active FROM users WHERE id=?",(uid,)).fetchone()
    return dict(row) if row else None

def require_auth():
    u = current_user()
    if not u or not u.get("active"):
        return None, (jsonify({"ok": False, "error": "unauthorized"}), 401)
    return u, None

def require_role(write=False):
    u, err = require_auth()
    if err: return None, err
    if write and u["role"] not in ("admin","manager"):
        return None, (jsonify({"ok": False, "error": "forbidden"}), 403)
    return u, None

# ---- Auth API ----
@app.route("/api/me")
def api_me():
    u = current_user()
    return jsonify({"ok": True, "authenticated": bool(u), "user": u})

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

# ---- Users (admin) ----
@app.route("/api/users", methods=["GET","POST","PATCH"])
def api_users():
    u, err = require_auth()
    if err: return err
    db = get_db()
    if request.method == "GET":
        if u["role"] != "admin":
            return jsonify({"ok": False, "error": "forbidden"}), 403
        rows = db.execute("SELECT id,email,name,role,active,created_at FROM users ORDER BY id").fetchall()
        return jsonify({"ok": True, "users":[dict(r) for r in rows]})
    if u["role"] != "admin":
        return jsonify({"ok": False, "error": "forbidden"}), 403
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
        updates = []; params = []
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

# ---- Jobs CRUD ----
@app.route("/api/jobs", methods=["GET","POST","PATCH","DELETE"])
def api_jobs():
    u, err = require_role(write=(request.method!="GET"))
    if err: return err
    db = get_db()
    if request.method == "GET":
        rows = db.execute("SELECT * FROM jobs ORDER BY date DESC, id DESC").fetchall()
        return jsonify({"ok": True, "jobs":[dict(r) for r in rows]})
    data = request.get_json(force=True, silent=True) or {}
    if request.method == "POST":
        req = ["title","client","city","code","date"]
        if not all(data.get(k) for k in req):
            return jsonify({"ok": False, "error":"invalid_input"}), 400
        status = data.get("status") or "Plán"
        db.execute("""INSERT INTO jobs(title,client,status,city,code,date)
                      VALUES (?,?,?,?,?,?)""",
                   (data["title"], data["client"], status, data["city"], data["code"], data["date"]))
        db.commit()
        return jsonify({"ok": True})
    if request.method == "PATCH":
        jid = data.get("id")
        if not jid:
            return jsonify({"ok": False, "error":"missing_id"}), 400
        fields = ["title","client","status","city","code","date"]
        updates = []; params = []
        for f in fields:
            if f in data:
                updates.append(f"{f}=?"); params.append(data[f])
        if not updates: return jsonify({"ok": False, "error":"nothing_to_update"}), 400
        params.append(jid)
        db.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id=?", params)
        db.commit()
        return jsonify({"ok": True})
    if request.method == "DELETE":
        jid = request.args.get("id", type=int)
        if not jid: return jsonify({"ok": False, "error":"missing_id"}), 400
        db.execute("DELETE FROM jobs WHERE id=?", (jid,))
        db.commit()
        return jsonify({"ok": True})

# ---- Employees CRUD ----
@app.route("/api/employees", methods=["GET","POST","PATCH","DELETE"])
def api_employees():
    u, err = require_role(write=(request.method!="GET"))
    if err: return err
    db = get_db()
    if request.method == "GET":
        rows = db.execute("SELECT * FROM employees ORDER BY id DESC").fetchall()
        return jsonify({"ok": True, "employees":[dict(r) for r in rows]})
    data = request.get_json(force=True, silent=True) or {}
    if request.method == "POST":
        name = data.get("name"); role = data.get("role")
        if not (name and role): return jsonify({"ok": False, "error":"invalid_input"}), 400
        db.execute("INSERT INTO employees(name,role) VALUES (?,?)", (name, role))
        db.commit()
        return jsonify({"ok": True})
    if request.method == "PATCH":
        eid = data.get("id")
        if not eid: return jsonify({"ok": False, "error":"missing_id"}), 400
        updates=[]; params=[]
        for f in ["name","role"]:
            if f in data: updates.append(f"{f}=?"); params.append(data[f])
        if not updates: return jsonify({"ok": False, "error":"nothing_to_update"}), 400
        params.append(eid)
        db.execute(f"UPDATE employees SET {', '.join(updates)} WHERE id=?", params)
        db.commit()
        return jsonify({"ok": True})
    if request.method == "DELETE":
        eid = request.args.get("id", type=int)
        if not eid: return jsonify({"ok": False, "error":"missing_id"}), 400
        db.execute("DELETE FROM employees WHERE id=?", (eid,))
        db.commit()
        return jsonify({"ok": True})

# ---- Warehouse Items CRUD ----
@app.route("/api/items", methods=["GET","POST","PATCH","DELETE"])
def api_items():
    u, err = require_role(write=(request.method!="GET"))
    if err: return err
    db = get_db()
    if request.method == "GET":
        site = request.args.get("site")
        q = "SELECT * FROM items" + (" WHERE site=?" if site in ("lipnik","praha") else "") + " ORDER BY id DESC"
        rows = db.execute(q, (site, ) if site in ("lipnik","praha") else ()).fetchall()
        return jsonify({"ok": True, "items":[dict(r) for r in rows]})
    data = request.get_json(force=True, silent=True) or {}
    if request.method == "POST":
        req = ["site","category","name","qty","unit"]
        if not all(k in data and data[k] not in (None,"") for k in req):
            return jsonify({"ok": False, "error":"invalid_input"}), 400
        if data["site"] not in ("lipnik","praha"):
            return jsonify({"ok": False, "error":"bad_site"}), 400
        db.execute("""INSERT INTO items(site,category,name,qty,unit) VALUES (?,?,?,?,?)""",
                   (data["site"], data["category"], data["name"], float(data["qty"]), data["unit"]))
        db.commit()
        return jsonify({"ok": True})
    if request.method == "PATCH":
        iid = data.get("id")
        if not iid: return jsonify({"ok": False, "error":"missing_id"}), 400
        updates=[]; params=[]
        for f in ["site","category","name","qty","unit"]:
            if f in data:
                if f=="site" and data[f] not in ("lipnik","praha"):
                    return jsonify({"ok": False, "error":"bad_site"}), 400
                updates.append(f"{f}=?")
                params.append(float(data[f]) if f=="qty" else data[f])
        if not updates: return jsonify({"ok": False, "error":"nothing_to_update"}), 400
        params.append(iid)
        db.execute(f"UPDATE items SET {', '.join(updates)} WHERE id=?", params)
        db.commit()
        return jsonify({"ok": True})
    if request.method == "DELETE":
        iid = request.args.get("id", type=int)
        if not iid: return jsonify({"ok": False, "error":"missing_id"}), 400
        db.execute("DELETE FROM items WHERE id=?", (iid,))
        db.commit()
        return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
