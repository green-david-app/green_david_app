
from fastapi import FastAPI, Form, UploadFile, File, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
import sqlite3
from contextlib import closing
from datetime import date
import io

try:
    from openpyxl import Workbook as WB
except Exception:
    WB = None

APP_TITLE = "green david app"
DB_PATH = "data.db"

app = FastAPI(title=APP_TITLE, description="Správa zakázek, skladu a zaměstnanců (CZ)", version="8.0")

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def column_exists(conn, table, col):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())

def init_db():
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY AUTOINCREMENT, jmeno TEXT NOT NULL, pozice TEXT);")
        c.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, nazev TEXT NOT NULL, zakaznik TEXT, poznamka TEXT);")
        c.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, nazev TEXT NOT NULL, mnozstvi REAL NOT NULL DEFAULT 0, jednotka TEXT NOT NULL DEFAULT 'ks');")
        c.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, typ TEXT NOT NULL, popis TEXT NOT NULL, hotovo INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);")
        c.execute("CREATE TABLE IF NOT EXISTS work_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, employee_id INTEGER NOT NULL, datum TEXT NOT NULL, hodiny REAL NOT NULL, poznamka TEXT, FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE, FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE);")
        c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value BLOB);")
        conn.commit()
        if not column_exists(conn, "work_entries", "poznamka"):
            c.execute("ALTER TABLE work_entries ADD COLUMN poznamka TEXT")
            conn.commit()

@app.on_event("startup")
def _startup():
    init_db()

def icon_svg(kind: str) -> str:
    if kind == "projects":
        return ("<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><rect x='3' y='4' width='18' height='14' rx='2'></rect><line x1='7' y1='8' x2='17' y2='8'></line><line x1='7' y1='12' x2='17' y2='12'></line></svg>")
    if kind == "stock":
        return ("<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'></path><polyline points='7 10 12 15 17 10'></polyline><line x1='12' y1='15' x2='12' y2='3'></line></svg>")
    if kind == "people":
        return ("<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M17 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2'></path><circle cx='9' cy='7' r='4'></circle><path d='M23 21v-2a4 4 0 0 0-3-3.87'></path><path d='M16 3.13a4 4 0 0 1 0 7.75'></path></svg>")
    return ""

def layout(body_html: str, subtitle: str = "") -> str:
    title = APP_TITLE if not subtitle else f"{APP_TITLE} · {subtitle}"
    with closing(get_conn()) as conn:
        has_logo = conn.execute("SELECT 1 FROM settings WHERE key='logo_mime'").fetchone() is not None
    logo = "<img src='/logo' alt='logo' style='height:28px;vertical-align:middle;margin-right:10px'>" if has_logo else ""
    header_content = f"<a href='/' style='display:flex;align-items:center;gap:10px;color:#fff;text-decoration:none'>{logo}<span>{APP_TITLE}</span></a>"
    tpl = """
<!DOCTYPE html>
<html lang="cs">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{TITLE}}</title>
  <style>
    :root {
      --bg:#e7f4ed;
      --box:#3e4347;
      --panel:#f3f5f7;
      --text-dark:#333333;
      --text-light:#ffffff;
      --accent:#69bb8a;
    }
    * { box-sizing: border-box; }
    body { background: var(--bg); color: var(--text-dark); font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif; margin:0; }
    header { background: var(--box); color: var(--text-light); padding:16px; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:22px; }
    main { padding:24px; max-width:1200px; margin:0 auto; }
    .grid { display:grid; grid-template-columns: 1fr; gap:22px; }
    @media (min-width: 980px) { .grid { grid-template-columns: 1fr 1fr; } }
    .box { background: var(--box); color: var(--text-light); border-radius:16px; padding:16px; box-shadow:0 2px 8px rgba(0,0,0,.08); }
    h2, h3 { margin:0 0 12px; display:flex; align-items:center; gap:8px; }
    .panel { background: var(--panel); color:#2f3a33; border-radius:12px; padding:12px; }
    .muted { color:#2f3a33aa; }
    form.inline { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
    input, textarea, select { padding:8px 10px; border-radius:8px; border:none; outline:none; background:#ffffff; color:#2f3a33; }
    input::placeholder, textarea::placeholder { color:#7a7a7a; }
    button { background: var(--accent); border:none; color:#fff; padding:8px 12px; border-radius:8px; cursor:pointer; }
    button:hover { filter: brightness(0.95); }
    a { color: inherit; text-decoration: underline; }
    .panel a { color:#333; }
    .box a { color:#fff; }
    .footer { position:fixed; bottom:0; left:0; right:0; background: var(--box); color: var(--text-light); text-align:center; padding:10px; }
    table { width:100%; border-collapse:collapse; }
    th, td { padding:8px 10px; border-bottom:1px solid #00000010; text-align:left; }
    .pill { display:inline-block; background:#ffffff; padding:2px 8px; border-radius:999px; font-size:12px; color:#2f3a33; }
    .task-toggle { background:#fff; color:#2f3a33; padding:2px 8px; border-radius:999px; font-size:12px; margin-left:8px; }
    .topbar { display:flex; gap:10px; align-items:center; justify-content:space-between; margin-bottom:14px; }
    .topbar a.small { font-size:13px; color:#ddd; }
  </style>
</head>
<body>
  <header>{{HEADER}}</header>
  <main>
    {{BODY_HTML}}
  </main>
  <div class="footer">© green david s.r.o.</div>
</body>
</html>
"""
    return (tpl.replace("{{TITLE}}", title)
              .replace("{{HEADER}}", header_content)
              .replace("{{BODY_HTML}}", body_html))

def projects_section():
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT id, nazev, zakaznik FROM projects ORDER BY id DESC").fetchall()
    if rows:
        lis = "".join([f"<tr><td><a href='/zakazka/{i}'>{n}</a></td><td class='muted'>{z or '—'}</td></tr>" for i,n,z in rows])
    else:
        lis = "<tr><td colspan='2' class='muted'>Žádné zakázky zatím nejsou.</td></tr>"
    html = f"""
    <div class="box">
      <h2>{icon_svg('projects')} Zakázky</h2>
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
    if rows:
        lis = "".join([f"<tr><td>{n}</td><td>{m:.2f}</td><td>{u}</td></tr>" for i,n,m,u in rows])
    else:
        lis = "<tr><td colspan='3' class='muted'>Žádné položky zatím nejsou.</td></tr>"
    html = f"""
    <div class="box">
      <h2>{icon_svg('stock')} Sklad</h2>
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

def employees_section():
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT id, jmeno, pozice FROM employees ORDER BY id DESC").fetchall()
        sums = {row[0]: 0 for row in rows}
        for rid in sums:
            h = conn.execute("SELECT COALESCE(SUM(hodiny),0) FROM work_entries WHERE employee_id=?", (rid,)).fetchone()[0]
            sums[rid] = float(h or 0)
    if rows:
        lis = "".join([f"<tr><td><a href='/zamestnanec/{i}'>{j}</a></td><td class='muted'>{p or '—'}</td><td><span class='pill'>{sums[i]:.2f} h</span></td></tr>" for i,j,p in rows])
    else:
        lis = "<tr><td colspan='3' class='muted'>Žádní zaměstnanci zatím nejsou.</td></tr>"
    html = f"""
    <div class="box">
      <div class="topbar">
        <h2>{icon_svg('people')} Zaměstnanci</h2>
        <a href="/nastaveni" class="small">Nastavení & Logo →</a>
      </div>
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

@app.get("/", response_class=HTMLResponse)
def home():
    body = "<div class='grid'>" + projects_section() + items_section() + employees_section() + "</div>"
    return HTMLResponse(layout(body))

@app.get("/zakazka/{pid}", response_class=HTMLResponse)
def project_detail(pid: int):
    with closing(get_conn()) as conn:
        p = conn.execute("SELECT id, nazev, zakaznik, poznamka FROM projects WHERE id=?", (pid,)).fetchone()
        if not p:
            return HTMLResponse(layout("<div class='box'>Zakázka nenalezena.</div>", "Zakázka"), status_code=404)
        tasks = conn.execute("SELECT id, typ, popis, hotovo FROM tasks WHERE project_id=? ORDER BY id DESC", (pid,)).fetchall()
        work = conn.execute("SELECT id, datum, employee_id, hodiny, poznamka FROM work_entries WHERE project_id=? ORDER BY datum DESC", (pid,)).fetchall()
        employees = conn.execute("SELECT id, jmeno FROM employees ORDER BY jmeno").fetchall()

    def list_tasks(t):
        subset = [r for r in tasks if r[1] == t]
        if not subset:
            return "<li class='muted'>nic zatím není</li>"
        return "".join([
            f"<li>{'✔️ ' if r[3] else ''}{r[2]}"
            f" <a class='task-toggle' href='/zakazka/{pid}/toggle-ukol/{r[0]}'>označit {'ne' if r[3] else 'ano'}</a>"
            f"</li>"
        for r in subset])

    work_rows = "".join([
        f"<tr><td>{d}</td>"
        f"<td>{next((n for i,n in employees if i==eid), '—')}</td>"
        f"<td>{h:.2f} h</td><td class='muted'>{(note or '').replace('<','&lt;')}</td></tr>"
        for (_id, d, eid, h, note) in work
    ]) or "<tr><td colspan='4' class='muted'>Žádné záznamy.</td></tr>"

    emp_opts = "".join([f"<option value='{i}'>{n}</option>" for i,n in employees])

    html = f"""
    <div class="box">
      <h2>{icon_svg('projects')} Zakázka: {p[1]}</h2>
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
              <thead><tr><th>Datum</th><th>Zaměstnanec</th><th>Hodin</th><th>Poznámka</th></tr></thead>
              <tbody>{work_rows}</tbody>
            </table>
          </div>
          <form class="inline" method="post" action="/zakazka/{p[0]}/pridat-hodiny">
            <input name="datum" type="date" value="{date.today().isoformat()}" required>
            <select name="employee_id">{emp_opts}</select>
            <input name="hodiny" type="number" step="0.25" value="8" required>
            <input name="poznamka" placeholder="Poznámka">
            <button type="submit">Zapsat</button>
          </form>
          <div style="margin-top:8px;">
            <a href="/zakazka/{p[0]}/export-xlsx">⬇️ Export XLSX</a>
          </div>
        </div>
      </div>
      <div style="margin-top:12px;"><a href="/">← Zpět na přehled</a></div>
    </div>
    """
    return HTMLResponse(layout(html, f"Zakázka {p[1]}"))

@app.get("/zamestnanec/{eid}", response_class=HTMLResponse)
def employee_detail(eid: int):
    with closing(get_conn()) as conn:
        emp = conn.execute("SELECT id, jmeno, pozice FROM employees WHERE id=?", (eid,)).fetchone()
        if not emp:
            return HTMLResponse(layout("<div class='box'>Zaměstnanec nenalezen.</div>", "Zaměstnanec"), status_code=404)
        rows = conn.execute("""
            SELECT we.datum, p.nazev, we.hodiny, COALESCE(we.poznamka,''), p.id
            FROM work_entries we
            JOIN projects p ON p.id = we.project_id
            WHERE we.employee_id=?
            ORDER BY we.datum DESC
        """,(eid,)).fetchall()
    total = sum(float(r[2]) for r in rows) if rows else 0.0
    lines = "".join([
        f"<tr><td>{d}</td><td><a href='/zakazka/{pid}'>{pname}</a></td><td>{float(h):.2f} h</td><td class='muted'>{note.replace('<','&lt;')}</td></tr>"
        for (d, pname, h, note, pid) in rows
    ]) or "<tr><td colspan='4' class='muted'>Žádné záznamy.</td></tr>"

    html = f"""
    <div class="box">
      <h2>{icon_svg('people')} Zaměstnanec: {emp[1]}</h2>
      <div class="panel" style="margin-bottom:12px;">
        <div><b>Pozice:</b> {emp[2] or '—'}</div>
        <div class="muted"><b>Celkem hodin:</b> {total:.2f} h</div>
      </div>
      <div class="panel">
        <table>
          <thead><tr><th>Datum</th><th>Zakázka</th><th>Hodin</th><th>Poznámka</th></tr></thead>
          <tbody>{lines}</tbody>
        </table>
      </div>
      <div style="margin-top:12px;"><a href="/">← Zpět na přehled</a></div>
    </div>
    """
    return HTMLResponse(layout(html, f"Zaměstnanec {emp[1]}"))

# Actions
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

@app.post("/zakazka/{pid}/pridat-ukol")
def add_task(pid: int, typ: str = Form(...), popis: str = Form(...)):
    if typ not in ("ukol","nakoupit","doresit"):
        typ = "ukol"
    with closing(get_conn()) as conn:
        conn.execute("INSERT INTO tasks (project_id, typ, popis) VALUES (?, ?, ?)", (pid, typ, popis))
        conn.commit()
    return RedirectResponse(f"/zakazka/{pid}", status_code=303)

@app.get("/zakazka/{pid}/toggle-ukol/{tid}")
def toggle_task(pid: int, tid: int):
    with closing(get_conn()) as conn:
        cur = conn.execute("SELECT hotovo FROM tasks WHERE id=?", (tid,)).fetchone()
        if cur:
            newv = 0 if cur[0] else 1
            conn.execute("UPDATE tasks SET hotovo=? WHERE id=?", (newv, tid))
            conn.commit()
    return RedirectResponse(f"/zakazka/{pid}", status_code=303)

@app.post("/zakazka/{pid}/pridat-hodiny")
def add_hours(pid: int, datum: str = Form(...), employee_id: int = Form(...), hodiny: float = Form(...), poznamka: str = Form(default="")):
    with closing(get_conn()) as conn:
        conn.execute("INSERT INTO work_entries (project_id, employee_id, datum, hodiny, poznamka) VALUES (?, ?, ?, ?, ?)", (pid, employee_id, datum, hodiny, poznamka or None))
        conn.commit()
    return RedirectResponse(f"/zakazka/{pid}", status_code=303)

@app.get("/zakazka/{pid}/export-xlsx")
def export_xlsx(pid: int):
    if WB is None:
        return HTMLResponse(layout("<div class='box'>Export není dostupný – chybí knihovna openpyxl.</div>", "Export"), status_code=501)
    with closing(get_conn()) as conn:
        p = conn.execute("SELECT id, nazev FROM projects WHERE id=?", (pid,)).fetchone()
        work = conn.execute("""
            SELECT we.datum, e.jmeno, we.hodiny, COALESCE(we.poznamka,'')
            FROM work_entries we
            JOIN employees e ON e.id = we.employee_id
            WHERE we.project_id=?
            ORDER BY we.datum
        """, (pid,)).fetchall()
    wb = WB()
    ws = wb.active
    ws.title = "Hodiny"
    ws.append(["Datum", "Zaměstnanec", "Hodiny", "Poznámka"])
    total = 0.0
    for d, j, h, note in work:
        ws.append([d, j, float(h), note])
        total += float(h)
    ws.append([])
    ws.append(["Celkem hodin", total])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"zakazka_{(p[1] if p else 'export').replace(' ','_')}_hodiny.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}"})

@app.get("/nastaveni", response_class=HTMLResponse)
def settings_page():
    html = """
    <div class="box">
      <h2>Nastavení</h2>
      <div class="panel">
        <p>Logo firmy: nahrajte PNG/JPG/SVG – bude uprostřed horní lišty a funguje jako tlačítko „zpět na přehled“ (klik na lištu).</p>
        <form method="post" action="/upload-logo" enctype="multipart/form-data">
          <input type="file" name="logo" accept="image/*" required>
          <button type="submit">Nahrát logo</button>
        </form>
      </div>
      <div style="margin-top:12px;"><a href="/">← Zpět</a></div>
    </div>
    """
    return HTMLResponse(layout(html, "Nastavení"))

@app.post("/upload-logo")
async def upload_logo(logo: UploadFile = File(...)):
    data = await logo.read()
    mime = logo.content_type or "image/png"
    with closing(get_conn()) as conn:
        conn.execute("REPLACE INTO settings (key, value) VALUES ('logo_blob', ?)", (sqlite3.Binary(data),))
        conn.execute("REPLACE INTO settings (key, value) VALUES ('logo_mime', ?)", (mime,))
        conn.commit()
    return RedirectResponse("/nastaveni", status_code=303)

@app.get("/logo")
def serve_logo():
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='logo_blob'").fetchone()
        mime = conn.execute("SELECT value FROM settings WHERE key='logo_mime'").fetchone()
    if not row:
        return Response(status_code=404)
    content = row[0]
    return Response(content, media_type=mime[0] if mime else "image/png")
