from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import User

auth_bp = Blueprint("auth", __name__)

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
        # zjistíme, zda už existuje (kvůli návratovému kódu 200/201)
        existed = db.session.execute(
            text("SELECT id FROM users WHERE email=:email LIMIT 1"),
            {"email": email}
        ).scalar()

        # UPSERT: vytvoří nebo aktualizuje podle e-mailu
        res = db.session.execute(
            text("""
                INSERT INTO users (email, password_hash, name, role)
                VALUES (:email, :ph, NULLIF(:name,''), COALESCE(NULLIF(:role,''),'user'))
                ON CONFLICT (email) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    name = COALESCE(NULLIF(EXCLUDED.name,''), users.name),
                    role = COALESCE(NULLIF(EXCLUDED.role,''), users.role)
                RETURNING id
            """),
            {"email": email, "ph": generate_password_hash(password), "name": name, "role": role}
        )
        user_id = res.scalar()
        db.session.commit()

        msg = "Účet aktualizován." if existed else "Uživatel vytvořen."
        code = 200 if existed else 201
        return jsonify({"message": msg, "id": user_id}), code

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

    return jsonify({"message": "Přihlášení úspěšné.", "user": {
        "id": user.id, "email": user.email, "name": user.name, "role": user.role
    }}), 200


@auth_bp.get("/users")
def list_users():
    users = User.query.order_by(User.id).all()
    return jsonify([
        {"id": u.id, "email": u.email, "name": u.name, "role": u.role,
         "created_at": u.created_at.isoformat() if u.created_at else None}
        for u in users
    ])
