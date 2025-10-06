from sqlalchemy import Integer, String, Text, Boolean, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="worker")
    password: Mapped[str] = mapped_column(String(200), nullable=False)  # plain for simplicity (can be hashed later)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    client: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Plán")
    city: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped = mapped_column(DateTime, server_default=func.now(), nullable=False)

class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="nový")
    employee_id: Mapped[int | None] = mapped_column(Integer)
    job_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped = mapped_column(DateTime, server_default=func.now(), nullable=False)

class Timesheet(Base):
    __tablename__ = "timesheets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int | None] = mapped_column(Integer)
    employee_id: Mapped[int | None] = mapped_column(Integer)
    date: Mapped[str] = mapped_column(String(20), nullable=False)
    hours: Mapped[float] = mapped_column(Numeric(6,2), nullable=False)
    place: Mapped[str | None] = mapped_column(Text)
    activity: Mapped[str | None] = mapped_column(Text)

class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    qty: Mapped[float] = mapped_column(Numeric(12,2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

class Tool(Base):
    __tablename__ = "tools"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    qty: Mapped[float] = mapped_column(Numeric(12,2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

class WarehouseItem(Base):
    __tablename__ = "warehouse"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site: Mapped[str] = mapped_column(String(40), nullable=False)  # lipnik / praha
    category: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    qty: Mapped[float] = mapped_column(Numeric(12,2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

class JobAssignment(Base):
    __tablename__ = "job_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False)

class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped = mapped_column(DateTime, server_default=func.now(), nullable=False)
