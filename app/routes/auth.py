import os
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import User

auth_bp = Blueprint("auth", __name__)

# ---- jen ty smíš registrovat nové uživatele ----
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

def _require_admin():
    token = request.headers.get("X-Admin-Token", "")
    return not ADMIN_TOKEN or token != ADMIN_TOKEN  # True = zakázat

def _col_exists(table: str, col: str) -> bool:
    q = text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name = :t AND column_name = :c
        LIMIT 1
    """)
    return db.session.execute(q, {"t": table, "c": col}).scalar() is not None

@auth_bp.post("/register")
def register():
    # zamčeno admin tokenem
    if _require_admin():
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()
    role = (data.get("role") or "user").strip() or "user"

    if not email or not password:
        return jsonify({"error": "Email a heslo jsou povinné."}), 400

    try:
        existed = db.session.execute(
            text("SELECT id FROM users WHERE email = :email LIMIT 1"),
            {"email": email}
        ).scalar()

        has_legacy_password = _col_exists("users", "password")
        has_active = _col_exists("users", "active")

        cols = ["email", "password_hash", "name", "role"]
        vals = [":email", ":ph", "NULLIF(:name,'')", "COALESCE(NULLIF(:role,''),'user')"]
        updates = [
            "password_hash = EXCLUDED.password_hash",
            "name = COALESCE(NULLIF(EXCLUDED.name,''), users.name)",
            "role = COALESCE(NULLIF(EXCLUDED.role,''), users.role)",
        ]
        params = {
            "email": email,
            "ph": generate_password_hash(password),
            "name": name,
            "role": role,
        }

        if has_legacy_password:
            cols.insert(1, "password")
            vals.insert(1, ":pw_legacy")
            updates.insert(0, "password = EXCLUDED.password")
            params["pw_legacy"] = params["ph"]

        if has_active:
            cols.append("active")
            vals.append(":active")
            params["active"] = True

        sql = f"""
            INSERT INTO users ({", ".join(cols)})
            VALUES ({", ".join(vals)})
            ON CONFLICT (email) DO UPDATE SET
                {", ".join(updates)}
            RETURNING id
        """
        user_id = db.session.execute(text(sql), params).scalar()
        db.session.commit()

        return jsonify(
            {"message": ("Účet aktualizován." if existed else "Uživatel vytvořen."), "id": user_id}
        ), (200 if existed else 201)

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Konflikt dat", "detail": str(e)}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Server error", "detail": str(e)}), 500

@auth_bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "Email a heslo jsou povinné."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Neplatné přihlašovací údaje."}), 401

    return jsonify({
        "message": "Přihlášení úspěšné.",
        "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role}
    }), 200

@auth_bp.get("/users")
def list_users():
    # seznam nechám taky jen pro tebe; když chceš veřejný, tuhle podmínku smaž
    if _require_admin():
        return jsonify({"error": "Forbidden"}), 403

    users = User.query.order_by(User.id).all()
    return jsonify([
        {"id": u.id, "email": u.email, "name": u.name, "role": u.role,
         "created_at": u.created_at.isoformat() if u.created_at else None}
        for u in users
    ])
