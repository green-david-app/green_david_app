from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from sqlmodel import SQLModel, Field, create_engine, Session, select

app = FastAPI(title="green david app", description="Správa zakázek, skladu a zaměstnanců (CZ)", version="1.1")

# Databázový model
class Employee(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    jmeno: str
    pozice: str | None = None

class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nazev: str
    zakaznik: str | None = None
    poznamka: str | None = None

class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nazev: str
    mnozstvi: float = 0
    jednotka: str = "ks"

# Databáze
engine = create_engine("sqlite:///data.db", echo=False)
SQLModel.metadata.create_all(engine)

def get_all(session, model):
    return session.exec(select(model)).all()

# Hlavní stránka
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    with Session(engine) as session:
        zamestnanci = get_all(session, Employee)
        zakazky = get_all(session, Project)
        polozky = get_all(session, Item)

    html = f"""
    <!DOCTYPE html>
    <html lang='cs'>
    <head>
        <meta charset='UTF-8'>
        <title>green david app</title>
        <style>
            body { background-color: #f5f5f5; font-family: Arial, sans-serif; color: #ffffff; margin: 0; padding: 0; }
            header { background-color: #9fd5b0; text-align: center; padding: 1rem; font-size: 1.8rem; font-weight: bold; }
            main { display: flex; flex-direction: column; align-items: center; padding: 2rem; }
            section { background-color: #9fd5b0; width: 80%; border-radius: 10px; margin-bottom: 1.5rem; padding: 1rem;
                      box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
            h2 { color: #ffffff; border-bottom: 1px solid #ffffff55; padding-bottom: 0.5rem; }
            li { margin-bottom: 0.3rem; }
            footer { text-align: center; padding: 1rem; color: #ffffffcc; font-size: 0.9rem; background-color: #9fd5b0;
                     position: fixed; bottom: 0; width: 100%; }
        </style>
    </head>
    <body>
        <header>🌿 green david app</header>
        <main>
            <section>
                <h2>👷 Zaměstnanci</h2>
                <ul>
                    {''.join(f'<li>{z.jmeno} – {z.pozice or "neuvedeno"}</li>' for z in zamestnanci) or '<li>Žádní zaměstnanci zatím nejsou.</li>'}
                </ul>
            </section>
            <section>
                <h2>📋 Zakázky</h2>
                <ul>
                    {''.join(f'<li>{p.nazev} – {p.zakaznik or "bez zákazníka"}</li>' for p in zakazky) or '<li>Žádné zakázky zatím nejsou.</li>'}
                </ul>
            </section>
            <section>
                <h2>📦 Sklad</h2>
                <ul>
                    {''.join(f'<li>{i.nazev} – {i.mnozstvi} {i.jednotka}</li>' for i in polozky) or '<li>Žádné položky zatím nejsou.</li>'}
                </ul>
            </section>
        </main>
        <footer>© green david s.r.o.</footer>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
