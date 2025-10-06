# Render fix: add Gunicorn + start command

This bundle contains:
- `requirements.txt` — now includes **gunicorn** so Render can run `gunicorn main:app`.
- `render.yaml` — (optional) if you commit this to the repo root, Render will auto-use the provided build & start commands.

## What to do
1) Replace your project's `requirements.txt` with the one here (or just add a line `gunicorn` to yours).
2) (Optional) Add `render.yaml` to the repo root.
3) Push to GitHub → Render will redeploy.
4) In Render dashboard, **Start Command** should be: `gunicorn main:app`.
   - Change `main:app` to match your module if needed (e.g., `app:app` when your file is `app.py`).

If you still see `bash: gunicorn: command not found`, it means the new `requirements.txt` wasn’t installed — trigger a “Clear build cache & deploy” on Render.
