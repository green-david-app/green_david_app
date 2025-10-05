from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field

class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    jmeno: str
    pozice: Optional[str] = None

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nazev: str
    zakaznik: Optional[str] = None
    termin: Optional[date] = None
    poznamka: Optional[str] = None

class Item(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nazev: str
    mnozstvi: float = 0
    jednotka: str = "ks"
