
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
from contextlib import closing

APP_TITLE = "green david app"
DB_PATH = "data.db"

app = FastAPI(title=APP_TITLE, description="Správa zakázek, skladu a zaměstnanců (CZ)", version="2.1")

# --- DB helpers ---
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jmeno TEXT NOT NULL,
                pozice TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nazev TEXT NOT NULL,
                zakaznik TEXT,
                poznamka TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nazev TEXT NOT NULL,
                mnozstvi REAL NOT NULL DEFAULT 0,
                jednotka TEXT NOT NULL DEFAULT 'ks'
            );
        """)
        conn.commit()

@app.on_event("startup")
def _startup():
    init_db()

# --- HTML UI ---
def layout(body_html: str) -> str:
    # Použijeme percent-formatting, aby se nemusely escapovat složené závorky v CSS
    tpl = """<!DOCTYPE html>
<html lang="cs">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>%s</title>
  <style>
    body { background:#f5f5f5; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif; color:#fff; margin:0; }
    header { background:#9fd5b0; padding:16px; text-align:center; font-weight:700; font-size:22px; }
    main { padding:24px; max-width:1000px; margin:0 auto; }
    .box { background:#9fd5b0; border-radius:12px; padding:16px; margin-bottom:18px; box-shadow:0 2px 6px rgba(0,0,0,.1); }
    h2 { margin:0 0 10px; border-bottom:1px solid #ffffff55; padding-bottom:8px; }
    ul { margin:8px 0 0; padding-left:20px; }
    li { margin:4px 0; }
    form.inline { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
    input, textarea { padding:8px 10px; border-radius:8px; border:none; outline:none; background:#ffffff33; color:#fff; }
    input::placeholder, textarea::placeholder { color:#ffffffaa; }
    button { background:#7fc89b; border:none; color:#fff; padding:8px 12px; border-radius:8px; cursor:pointer; }
    button:hover { background:#72be90; }
    footer { position:fixed; bottom:0; left:0; right:0; background:#9fd5b0; text-align:center; color:#ffffffcc; padding:10px; }
    .grid { display:grid; grid-template-columns: 1fr; gap:18px; }
    @media (min-width: 900px) { .grid { grid-template-columns: 1fr 1fr; } }
  </style>
</head>
<body>
  <header>🌿 %s</header>
  <main>
    %s
  </main>
  <footer>© green david s.r.o.</footer>
</body>
</html>"""
    return tpl % (APP_TITLE, APP_TITLE, body_html)

def section_employees():
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT id, jmeno, pozice FROM employees ORDER BY id DESC").fetchall()
    items = "".join([f"<li>{j} – {p or 'neuvedeno'}</li>" for _, j, p in rows]) or "<li>Žádní zaměstnanci zatím nejsou.</li>"
    return """
    <div class="box">
      <h2>👷 Zaměstnanci</h2>
      <ul>%s</ul>
      <form class="inline" method="post" action="/pridat-zamestnance">
        <input name="jmeno" placeholder="Jméno" required>
        <input name="pozice" placeholder="Pozice">
        <button type="submit">Přidat</button>
      </form>
    </div>
    """ % items

def section_projects():
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT id, nazev, zakaznik FROM projects ORDER BY id DESC").fetchall()
    items = "".join([f"<li>{n} – {z or 'bez zákazníka'}</li>" for _, n, z in rows]) or "<li>Žádné zakázky zatím nejsou.</li>"
    return """
    <div class="box">
      <h2>📋 Zakázky</h2>
      <ul>%s</ul>
      <form class="inline" method="post" action="/pridat-zakazku">
        <input name="nazev" placeholder="Název zakázky" required>
        <input name="zakaznik" placeholder="Zákazník">
        <input name="poznamka" placeholder="Poznámka">
        <button type="submit">Přidat</button>
      </form>
    </div>
    """ % items

def section_items():
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT id, nazev, mnozstvi, jednotka FROM items ORDER BY id DESC").fetchall()
    items = "".join([f"<li>{n} – {m} {u}</li>" for _, n, m, u in rows]) or "<li>Žádné položky zatím nejsou.</li>"
    return """
    <div class="box">
      <h2>📦 Sklad</h2>
      <ul>%s</ul>
      <form class="inline" method="post" action="/pridat-polozku">
        <input name="nazev" placeholder="Název položky" required>
        <input name="mnozstvi" placeholder="Množství" type="number" step="0.01" value="0">
        <input name="jednotka" placeholder="Jednotka" value="ks">
        <button type="submit">Přidat</button>
      </form>
    </div>
    """ % items

@app.get("/", response_class=HTMLResponse)
def index():
    body = '<div class="grid">%s%s%s</div>' % (section_employees(), section_projects(), section_items())
    return HTMLResponse(layout(body))

# --- Actions ---
@app.post("/pridat-zamestnance")
def pridat_zamestnance(jmeno: str = Form(...), pozice: str | None = Form(default=None)):
    with closing(get_conn()) as conn:
        conn.execute("INSERT INTO employees (jmeno, pozice) VALUES (?, ?)", (jmeno, pozice))
        conn.commit()
    return RedirectResponse("/", status_code=303)

@app.post("/pridat-zakazku")
def pridat_zakazku(nazev: str = Form(...), zakaznik: str | None = Form(default=None), poznamka: str | None = Form(default=None)):
    with closing(get_conn()) as conn:
        conn.execute("INSERT INTO projects (nazev, zakaznik, poznamka) VALUES (?, ?, ?)", (nazev, zakaznik, poznamka))
        conn.commit()
    return RedirectResponse("/", status_code=303)

@app.post("/pridat-polozku")
def pridat_polozku(nazev: str = Form(...), mnozstvi: float = Form(default=0), jednotka: str = Form(default="ks")):
    with closing(get_conn()) as conn:
        conn.execute("INSERT INTO items (nazev, mnozstvi, jednotka) VALUES (?, ?, ?)", (nazev, mnozstvi, jednotka))
        conn.commit()
    return RedirectResponse("/", status_code=303)
