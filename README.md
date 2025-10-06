# green_david_app (fixed)

Opravené soubory pro Render:
- Opraven překlep `sqlalchmy` → `sqlalchemy` (v importu `from sqlalchemy.exc import IntegrityError`).
- Doplněn `requirements.txt` se závislostmi včetně `SQLAlchemy` a `Flask-SQLAlchemy`.
- Přidán `Procfile` s příkazem `web: gunicorn main:app`.
- Minimalní struktura Flask aplikace s registrací a přihlášením.

## Nasazení na Render
1. Nahrajte ZIP tohoto repozitáře.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn main:app`
4. Databáze: připojte Render PostgreSQL (proměnná `DATABASE_URL` se vytvoří automaticky).
