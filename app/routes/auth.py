from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import User

auth_bp = Blueprint("auth", __name__)

def _col_exists(table: str, col: str) -> bool:
    q = text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :t AND column_name = :c
        LIMIT 1
    """)
    return db.session.execute(q, {"t": table, "c": col}).scalar() is not None

@auth_bp.post("/register")
def register():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()
    role = (data.get("role") or "user").strip() or "user"

    if not email or not password:
        return jsonify({"error": "Email a heslo jsou povinné."}), 400

    try:
        # Zjistíme, zda e-mail už existuje (kvůli návratovému kódu 200/201)
        existed = db.session.execute(
            text("SELECT id FROM users WHERE email = :email LIMIT 1"),
            {"email": email}
        ).scalar()

        # Legacy sloupce ve staré tabulce?
        has_legacy_password = _col_exists("users", "password")

        # Připravíme dynamický UPSERT
        columns = ["email", "password_hash", "name", "role"]
        values  = [":email", ":ph", "NULLIF(:name,'')", "COALESCE(NULLIF(:role,''),'user')"]
        updates = [
            "password_hash = EXCLUDED.password_hash",
            "name = COALESCE(NULLIF(EXCLUDED.name,''), users.name)",
            "role = COALESCE(NULLIF(EXCLUDED.role,''), users.role)"
        ]
        params = {
            "email": email,
            "ph": generate_password_hash(password),
            "name": name,
            "role": role
        }

        # Pokud existuje legacy sloupec "password" (NOT NULL ve starém schématu),
        # naplníme ho také (hashovanou hodnotou), aby insert nepadal.
        if has_legacy_password:
            columns.insert(1, "password")
            values.insert(1, ":pw_legacy")
            updates.insert(0, "password = EXCLUDED.password")
            params["pw_legacy"] = params["ph"]

        sql = f"""
            INSERT INTO users ({", ".join(columns)})
            VALUES ({", ".join(values)})
            ON CONFLICT (email) DO UPDATE SET
                {", ".join(updates)}
            RETURNING id
        """

        user_id = db.session.execute(text(sql), params).scalar()
        db.session.commit()

        return jsonify({"message": ("Účet aktualizován." if existed else "Uživatel vytvořen."), "id": user_id}), (200 if existed else 201)

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
    users = User.query.order_by(User.id).all()
    return jsonify([
        {"id": u.id, "email": u.email, "name": u.name, "role": u.role,
         "created_at": u.created_at.isoformat() if u.created_at else None}
        for u in users
    ])
