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

    try:
        user = User(email=email, password_hash=generate_password_hash(password), name=name, role=role)
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "Uživatel vytvořen.", "id": user.id}), 201
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Uživatel s tímto emailem již existuje."}), 409

