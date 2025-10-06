# wsgi.py
# Universal WSGI entrypoint for Gunicorn on Render.
# It tries to import the Flask/FastAPI 'app' object from your project.
# Supported common layouts:
#   - main.py with `app = ...`
#   - app.py  with `app = ...`
#   - package module `app/__init__.py` exposing `app`
#
# Gunicorn start command on Render:
#   gunicorn wsgi:app -b 0.0.0.0:$PORT -w 2 -k gthread
#
# After adding this file, you don't need to rename your existing files.
# Just ensure your application exposes a top-level variable named `app`.

try:
    # Most common: project root has main.py with `app = Flask(...)` (or FastAPI)
    from main import app  # type: ignore
except Exception:
    try:
        # Alternative: project root has app.py
        from app import app  # type: ignore
    except Exception:
        try:
            # Package layout: app/__init__.py defines `app`
            from app import app as app  # type: ignore
        except Exception as e:
            raise ImportError(
                "WSGI failed to import your application. Ensure that your project "
                "exposes a top-level variable named 'app' in main.py, app.py, or app/__init__.py."
            ) from e
