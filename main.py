
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
import sqlite3
from contextlib import closing
from datetime import date
from typing import Optional

APP_TITLE = "green david app"
DB_PATH = "data.db"
LOGO_URL: Optional[str] = ""  # ← Sem můžeš vložit URL loga (např. "https://.../logo.png")

app = FastAPI(title=APP_TITLE, description="Správa zakázek, skladu a zaměstnanců (CZ)", version="3.0")

# --- DB helpers ---
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jmeno TEXT NOT NULL,
                pozice TEXT
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nazev TEXT NOT NULL,
                zakaznik TEXT,
                poznamka TEXT
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nazev TEXT NOT NULL,
                mnozstvi REAL NOT NULL DEFAULT 0,
                jednotka TEXT NOT NULL DEFAULT 'ks'
            );
        """)
        # Přidáno: úkoly k zakázce
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                typ TEXT NOT NULL,     -- 'ukol' | 'nakoupit' | 'doresit'
                popis TEXT NOT NULL,
                hotovo INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
        """)
        # Přidáno: evidence práce (k zakázce, v konkrétní den, pro zaměstnance)
        c.execute("""
            CREATE TABLE IF NOT EXISTS work_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                datum TEXT NOT NULL,   -- ISO yyyy-mm-dd
                hodiny REAL NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );
        """)
        conn.commit()

@app.on_event("startup")
def _startup():
    init_db()

# --- Templating ---
def layout(body_html: str, subtitle: str = "") -> str:
    title = f"{APP_TITLE}" if not subtitle else f"{APP_TITLE} · {subtitle}"
    tpl = """<!DOCTYPE html>
<html lang="cs">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>%s</title>
  <style>
    :root {
      --green:#cfeedd;        /* světlejší zelená pozadí */
      --green-box:#a8d5ba;    /* pastelově zelená boxy (světlejší než předtím) */
      --grey:#e9ecef;         /* ŠEDÁ na plochy uvnitř boxu */
      --text:#ffffff;
      --text-dim:#ffffffcc;
    }
    * { box-sizing: border-box; }
    body { background: var(--green); font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif; color: var(--text); margin:0; }
    header { background: var(--green-box); padding:16px; text-align:center; font-weight:800; font-size:22px; display:flex; align-items:center; justify-content:center; gap:12px; }
    header img { height:28px; width:auto; object-fit:contain; }
    main { padding:24px; max-width:1200px; margin:0 auto; }
    .grid { display:grid; grid-template-columns: 1fr; gap:22px; }
    @media (min-width: 980px) { .grid { grid-template-columns: 1fr 1fr; } }
    .box { background: var(--green-box); border-radius:16px; padding:16px; box-shadow:0 2px 8px rgba(0,0,0,.08); }
    h2 { margin:0 0 12px; }
    .panel { background: var(--grey); color:#2f3a33; border-radius:12px; padding:12px; }
    .muted { color:#2f3a33aa; }
    form.inline { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
    input, textarea, select { padding:8px 10px; border-radius:8px; border:none; outline:none; background:#ffffff; color:#2f3a33; }
    input::placeholder, textarea::placeholder { color:#7a7a7a; }
    button { background:#7fc89b; border:none; color:#fff; padding:8px 12px; border-radius:8px; cursor:pointer; }
    button:hover { background:#72be90; }
    a { color:#1f6f4a; text-decoration:none; font-weight:600; }
    .footer { position:fixed; bottom:0; left:0; right:0; background: var(--green-box); text-align:center; color: var(--text-dim); padding:10px; }
    table { width:100%; border-collapse:collapse; }
    th, td { padding:8px 10px; border-bottom:1px solid #00000010; text-align:left; }
    .pill { display:inline-block; background:#ffffff; padding:2px 8px; border-radius:999px; font-size:12px; color:#2f3a33; }
  </style>
</head>
<body>
  <header>%s %s</header>
  <main>
    %s
  </main>
  <div class="footer">© green david s.r.o.</div>
</body>
</html>"""
    logo_html = f"<img src='{LOGO_URL}' alt='logo'>" if LOGO_URL else ""
    return tpl % (title, logo_html, APP_TITLE, body_html)

# --- Sekce: Zaměstnanci / Zakázky / Sklad ---
def employees_section():
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT id, jmeno, pozice FROM employees ORDER BY id DESC").fetchall()
        # Součty hodin za zaměstnance
        sums = {row[0]: 0 for row in rows}
        for rid in sums:
            h = conn.execute("SELECT COALESCE(SUM(hodiny),0) FROM work_entries WHERE employee_id=?", (rid,)).fetchone()[0]
            sums[rid] = h or 0
    lis = "".join([f"<tr><td>{j}</td><td class='muted'>{p or '—'}</td><td><span class='pill'>{sums[i]:.2f} h</span></td></tr>" for i,j,p in rows]) or "<tr><td colspan='3' class='muted'>Žádní zaměstnanci zatím nejsou.</td></tr>"
    html = f"""
    <div class="box">
      <h2>👷 Zaměstnanci</h2>
      <div class="panel">
        <table>
          <thead><tr><th>Jméno</th><th>Pozice</th><th>Odpracováno</th></tr></thead>
          <tbody>{lis}</tbody>
        </table>
      </div>
      <form class="inline" method="post" action="/pridat-zamestnance">
        <input name="jmeno" placeholder="Jméno" required>
        <input name="pozice" placeholder="Pozice">
        <button type="submit">Přidat</button>
      </form>
    </div>
    """
    return html

def projects_section():
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT id, nazev, zakaznik FROM projects ORDER BY id DESC").fetchall()
    lis = "".join([f"<tr><td><a href='/zakazka/{i}'>{n}</a></td><td class='muted'>{z or '—'}</td></tr>" for i,n,z in rows]) or "<tr><td colspan='2' class='muted'>Žádné zakázky zatím nejsou.</td></tr>"
    html = f"""
    <div class="box">
      <h2>📋 Zakázky</h2>
      <div class="panel">
        <table>
          <thead><tr><th>Název</th><th>Zákazník</th></tr></thead>
          <tbody>{lis}</tbody>
        </table>
      </div>
      <form class="inline" method="post" action="/pridat-zakazku">
        <input name="nazev" placeholder="Název zakázky" required>
        <input name="zakaznik" placeholder="Zákazník">
        <input name="poznamka" placeholder="Poznámka">
        <button type="submit">Přidat</button>
      </form>
    </div>
    """
    return html

def items_section():
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT id, nazev, mnozstvi, jednotka FROM items ORDER BY id DESC").fetchall()
    lis = "".join([f"<tr><td>{n}</td><td>{m:.2f}</td><td>{u}</td></tr>" for i,n,m,u in rows]) or "<tr><td colspan='3' class='muted'>Žádné položky zatím nejsou.</td></tr>"
    html = f"""
    <div class="box">
      <h2>📦 Sklad</h2>
      <div class="panel">
        <table>
          <thead><tr><th>Název</th><th>Množství</th><th>Jednotka</th></tr></thead>
          <tbody>{lis}</tbody>
        </table>
      </div>
      <form class="inline" method="post" action="/pridat-polozku">
        <input name="nazev" placeholder="Název položky" required>
        <input name="mnozstvi" placeholder="Množství" type="number" step="0.01" value="0">
        <input name="jednotka" placeholder="Jednotka" value="ks">
        <button type="submit">Přidat</button>
      </form>
    </div>
    """
    return html

@app.get("/", response_class=HTMLResponse)
def home():
    body = f"<div class='grid'>{employees_section()}{projects_section()}{items_section()}</div>"
    return HTMLResponse(layout(body))

# --- Detail zakázky: úkoly + kalendář hodin ---
@app.get("/zakazka/{pid}", response_class=HTMLResponse)
def project_detail(pid: int):
    with closing(get_conn()) as conn:
        p = conn.execute("SELECT id, nazev, zakaznik, poznamka FROM projects WHERE id=?", (pid,)).fetchone()
        if not p:
            return HTMLResponse(layout("<div class='box'>Zakázka nenalezena.</div>", "Zakázka"), status_code=404)
        # úkoly
        tasks = conn.execute("SELECT id, typ, popis, hotovo FROM tasks WHERE project_id=? ORDER BY id DESC", (pid,)).fetchall()
        # pracovní výkazy (posledních 30 dní)
        work = conn.execute("SELECT datum, employee_id, hodiny FROM work_entries WHERE project_id=? ORDER BY datum DESC", (pid,)).fetchall()
        employees = conn.execute("SELECT id, jmeno FROM employees ORDER BY jmeno").fetchall()

    def list_tasks(t):
        subset = [r for r in tasks if r[1] == t]
        if not subset:
            return "<li class='muted'>nic zatím není</li>"
        return "".join([f"<li>{'✔️ ' if r[3] else ''}{r[2]}</li>" for r in subset])

    work_rows = "".join([f"<tr><td>{d}</td><td>{next((n for i,n in employees if i==eid), '—')}</td><td>{h:.2f} h</td></tr>"
                         for (d, eid, h) in work]) or "<tr><td colspan='3' class='muted'>Žádné záznamy.</td></tr>"

    emp_opts = "".join([f"<option value='{i}'>{n}</option>" for i,n in employees])

    html = f"""
    <div class="box">
      <h2>Zakázka: {p[1]}</h2>
      <div class="panel" style="margin-bottom:12px;">
        <div><b>Zákazník:</b> {p[2] or '—'}</div>
        <div class="muted"><b>Poznámka:</b> {p[3] or '—'}</div>
      </div>

      <div class="grid">
        <div class="box">
          <h3>🧩 Úkoly</h3>
          <div class="panel">
            <b>Co udělat</b>
            <ul>{list_tasks('ukol')}</ul>
            <b>Co nakoupit</b>
            <ul>{list_tasks('nakoupit')}</ul>
            <b>Co dořešit</b>
            <ul>{list_tasks('doresit')}</ul>
          </div>
          <form class="inline" method="post" action="/zakazka/{p[0]}/pridat-ukol">
            <select name="typ">
              <option value="ukol">Ukol</option>
              <option value="nakoupit">Nakoupit</option>
              <option value="doresit">Dořešit</option>
            </select>
            <input name="popis" placeholder="Popis" required>
            <button type="submit">Přidat</button>
          </form>
        </div>

        <div class="box">
          <h3>🕒 Kalendář / odpracované hodiny</h3>
          <div class="panel">
            <table>
              <thead><tr><th>Datum</th><th>Zaměstnanec</th><th>Hodin</th></tr></thead>
              <tbody>{work_rows}</tbody>
            </table>
          </div>
          <form class="inline" method="post" action="/zakazka/{p[0]}/pridat-hodiny">
            <input name="datum" type="date" value="{date.today().isoformat()}" required>
            <select name="employee_id">{emp_opts}</select>
            <input name="hodiny" type="number" step="0.25" value="8" required>
            <button type="submit">Zapsat</button>
          </form>
        </div>
      </div>
      <div style="margin-top:12px;"><a href="/">← Zpět na přehled</a></div>
    </div>
    """
    return HTMLResponse(layout(html, f"Zakázka {p[1]}"))

# --- Actions (home) ---
@app.post("/pridat-zamestnance")
def add_employee(jmeno: str = Form(...), pozice: str = Form(default="")):
    with closing(get_conn()) as conn:
        conn.execute("INSERT INTO employees (jmeno, pozice) VALUES (?, ?)", (jmeno, pozice or None))
        conn.commit()
    return RedirectResponse("/", status_code=303)

@app.post("/pridat-zakazku")
def add_project(nazev: str = Form(...), zakaznik: str = Form(default=""), poznamka: str = Form(default="")):
    with closing(get_conn()) as conn:
        conn.execute("INSERT INTO projects (nazev, zakaznik, poznamka) VALUES (?, ?, ?)", (nazev, zakaznik or None, poznamka or None))
        conn.commit()
    return RedirectResponse("/", status_code=303)

@app.post("/pridat-polozku")
def add_item(nazev: str = Form(...), mnozstvi: float = Form(default=0), jednotka: str = Form(default="ks")):
    with closing(get_conn()) as conn:
        conn.execute("INSERT INTO items (nazev, mnozstvi, jednotka) VALUES (?, ?, ?)", (nazev, mnozstvi, jednotka))
        conn.commit()
    return RedirectResponse("/", status_code=303)

# --- Actions (project detail) ---
@app.post("/zakazka/{pid}/pridat-ukol")
def add_task(pid: int, typ: str = Form(...), popis: str = Form(...)):
    if typ not in ("ukol","nakoupit","doresit"):
        typ = "ukol"
    with closing(get_conn()) as conn:
        conn.execute("INSERT INTO tasks (project_id, typ, popis) VALUES (?, ?, ?)", (pid, typ, popis))
        conn.commit()
    return RedirectResponse(f"/zakazka/{pid}", status_code=303)

@app.post("/zakazka/{pid}/pridat-hodiny")
def add_hours(pid: int, datum: str = Form(...), employee_id: int = Form(...), hodiny: float = Form(...)):
    with closing(get_conn()) as conn:
        conn.execute("INSERT INTO work_entries (project_id, employee_id, datum, hodiny) VALUES (?, ?, ?, ?)", (pid, employee_id, datum, hodiny))
        conn.commit()
    return RedirectResponse(f"/zakazka/{pid}", status_code=303)
