import os
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from database import init_db
from models import User

def create_app():
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    Session = init_db(app)

    @app.get("/")
    def index():
        return jsonify({"ok": True, "message": "green-david-app API running"})

    # --- Users ---
    @app.post("/api/register")
    def register_user():
        payload = request.get_json(silent=True) or {}
        username = (payload.get("username") or "").strip()
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""

        if not username or not email or not password:
            return jsonify({"ok": False, "error": "MISSING_FIELDS",
                            "message": "username, email, password jsou povinné"}), 400

        # basic length checks
        if len(username) < 3:
            return jsonify({"ok": False, "error": "USERNAME_TOO_SHORT"}), 400
        if "@" not in email:
            return jsonify({"ok": False, "error": "EMAIL_INVALID"}), 400
        if len(password) < 6:
            return jsonify({"ok": False, "error": "PASSWORD_TOO_SHORT"}), 400

        session = Session()
        try:
            user = User(username=username, email=email, password_hash=generate_password_hash(password))
            session.add(user)
            session.commit()
            return jsonify({"ok": True, "user": user.to_safe_dict()}), 201
        except IntegrityError as e:
            session.rollback()
            # Determine which unique constraint failed
            msg = str(e.orig).lower()
            if "uq_users_email" in msg or "email" in msg:
                return jsonify({"ok": False, "error": "EMAIL_EXISTS", "message": "Email už existuje"}), 409
            if "uq_users_username" in msg or "username" in msg:
                return jsonify({"ok": False, "error": "USERNAME_EXISTS", "message": "Uživatelské jméno už existuje"}), 409
            return jsonify({"ok": False, "error": "INTEGRITY_ERROR"}), 400
        except Exception as e:
            session.rollback()
            return jsonify({"ok": False, "error": "SERVER_ERROR", "message": str(e)}), 500
        finally:
            session.close()

    @app.post("/api/login")
    def login():
        payload = request.get_json(silent=True) or {}
        email_or_username = (payload.get("email") or payload.get("username") or "").strip().lower()
        password = payload.get("password") or ""
        if not email_or_username or not password:
            return jsonify({"ok": False, "error": "MISSING_FIELDS"}), 400

        session = Session()
        try:
            # try email first, then username
            user = session.query(User).filter(User.email == email_or_username).first()
            if not user:
                user = session.query(User).filter(User.username == email_or_username).first()
            if not user or not check_password_hash(user.password_hash, password):
                return jsonify({"ok": False, "error": "INVALID_CREDENTIALS"}), 401
            return jsonify({"ok": True, "user": user.to_safe_dict()})
        finally:
            session.close()

    @app.get("/api/users")
    def list_users():
        session = Session()
        try:
            users = session.query(User).order_by(User.id.desc()).all()
            return jsonify({"ok": True, "users": [u.to_safe_dict() for u in users]})
        finally:
            session.close()

    # Static file serving (logo, css, uploads) if needed
    @app.get("/static/<path:filename>")
    def serve_static(filename):
        return send_from_directory("static", filename, as_attachment=False)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
