# Render deploy fix (Gunicorn + WSGI)

Your deploy is failing because `gunicorn` is not available:
`bash: line 1: gunicorn: command not found`

## What to upload
- `wsgi.py` (this file routes to your existing `app` object automatically)
- Add **one line** to your existing `requirements.txt`:
  ```
  gunicorn==21.2.0
  ```

## Render settings
In Render Dashboard → your Web Service → **Settings** → **Start Command**, set:
```
gunicorn wsgi:app -b 0.0.0.0:$PORT -w 2 -k gthread --timeout 120
```
> If you already had `gunicorn main:app`, replace it with the above.  
> Keep your existing Python version and build command as they are.

## Notes
- Ensure your application exposes a top-level variable named `app`, e.g.
  ```python
  # main.py or app.py
  from flask import Flask
  app = Flask(__name__)
  ```
  or for FastAPI:
  ```python
  from fastapi import FastAPI
  app = FastAPI()
  ```
- You **don’t** need to rename any of your files; `wsgi.py` handles both `main.py` and `app.py`.
- No Procfile is needed on Render.

## Optional: create folders at build (for uploads/static)
If your app needs `static/` and `uploads/`, make sure they exist in the repo, or create them on first run.
You can safely add empty folders to git by placing a `.gitkeep` file inside each.
