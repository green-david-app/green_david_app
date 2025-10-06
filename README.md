# green-david-app – fix multi-user registration

## Quick start (local)
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Test
```bash
curl -X POST http://127.0.0.1:5000/api/register -H "Content-Type: application/json"   -d '{"username":"david","email":"david@example.com","password":"heslo123"}'
```

## Render
- Set `START_CMD` to `gunicorn main:app` or `python main.py`
- Optional `DATABASE_URL` env var (Postgres). If not set, SQLite `app.db` is used.
- The app creates `static/uploads` automatically.
