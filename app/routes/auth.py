from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/register")
def register():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = data.get("name") or ""
    role = data.get("role") or "user"

    if not email or not password:
        return jsonify({"error": "Email a heslo jsou povinné."}), 400

    # UPSERT: existuje? -> update; jinak -> create
    existing = User.query.filter_by(email=email).first()
    try:
        if existing:
            existing.password_hash = generate_password_hash(password)
            if name:
                existing.name = name
            if not existing.role:
                existing.role = role
            db.session.commit()
            return jsonify({"message": "Účet aktualizován.", "id": existing.id}), 200

        user = User(email=email, password_hash=generate_password_hash(password), name=name, role=role)
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "Uživatel vytvořen.", "id": user.id}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Uživatel s tímto emailem již existuje."}), 409
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
