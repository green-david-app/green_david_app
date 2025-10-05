from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security.api_key import APIKeyHeader
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from database import init_db, get_session
from models import Employee, Project, Item

API_KEY = "demo-secret-key"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def over_api_klic(x_api_key: str = Depends(api_key_header)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Neplatný nebo chybějící API klíč")

app = FastAPI(title="green david app", description="Správa zakázek, skladu a zaměstnanců (CZ)", version="1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def inicializace():
    init_db()

@app.get("/", response_class=HTMLResponse)
def uvod(request: Request, session: Session = Depends(get_session)):
    zamestnanci = session.exec(select(Employee)).all()
    zakazky = session.exec(select(Project)).all()
    polozky = session.exec(select(Item)).all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "zamestnanci": zamestnanci,
        "zakazky": zakazky,
        "polozky": polozky
    })

@app.get("/zamestnanci", dependencies=[Depends(over_api_klic)])
def seznam_zamestnancu(session: Session = Depends(get_session)):
    return session.exec(select(Employee)).all()

@app.get("/zakazky", dependencies=[Depends(over_api_klic)])
def seznam_zakazek(session: Session = Depends(get_session)):
    return session.exec(select(Project)).all()

@app.get("/polozky", dependencies=[Depends(over_api_klic)])
def seznam_polozek(session: Session = Depends(get_session)):
    return session.exec(select(Item)).all()
