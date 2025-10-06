import os, io, base64, re, secrets, uuid
from flask import Flask, request, send_from_directory, jsonify, send_file
from flask_session import Session
from sqlalchemy import select, delete, update
from sqlalchemy.orm import Session as DBSession
from database import engine, SessionLocal, Base
from models import User, Job, Employee, Task, Timesheet, Material, Tool, WarehouseItem, JobAssignment, Photo
from openpyxl import Workbook

APP_TITLE = "green david app"

def create_app():
    app = Flask(__name__, static_folder=None)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY","admin123")
    app.config["SESSION_TYPE"] = "filesystem"  # simple persistent cookie sessions; swap to sqlalchemy if wanted
    Session(app)

    # create tables
    Base.metadata.create_all(bind=engine)

    # seed default admin if not exists
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email=="admin@greendavid.local")):
            db.add(User(email="admin@greendavid.local", name="Admin", role="admin", password="admin123", active=True))
            db.commit()

    # ---- Static files ----
    @app.get("/")
    def root():
        return send_from_directory(".", "index.html")

    @app.get("/style.css")
    def css():
        return send_from_directory(".", "style.css")

    @app.get("/logo.jpg")
    def logo_jpg():
        return send_from_directory(".", "logo.jpg") if os.path.exists("logo.jpg") else ("",404)

    @app.get("/logo.svg")
    def logo_svg():
        return send_from_directory(".", "logo.svg") if os.path.exists("logo.svg") else ("",404)

    @app.get("/uploads/<path:fname>")
    def uploads(fname):
        return send_from_directory("static/uploads", fname)

    # ---- Auth ----
    def current_user():
        uid = request.cookies.get("uid")
        if not uid:
            return None
        try:
            uid=int(uid)
        except:
            return None
        with SessionLocal() as db:
            return db.get(User, uid)

    @app.get("/api/me")
    def api_me():
        u = current_user()
        if not u:
            return jsonify({"authenticated": False})
        with SessionLocal() as db:
            count = db.scalar(select(Task).count()) or 0
        return jsonify({"authenticated": True, "user":{"id":u.id,"email":u.email,"name":u.name,"role":u.role}, "tasks_count": count})

    @app.post("/api/login")
    def api_login():
        data = request.get_json(force=True)
        email = data.get("email","").strip().lower()
        password = data.get("password","")
        with SessionLocal() as db:
            u = db.scalar(select(User).where(User.email==email))
            if not u or u.password != password or not u.active:
                return jsonify({"error":"Bad credentials"}), 401
        resp = jsonify({"ok": True})
        resp.set_cookie("uid", str(u.id), httponly=True, samesite="Lax")
        return resp

    @app.post("/api/logout")
    def api_logout():
        resp = jsonify({"ok": True})
        resp.delete_cookie("uid")
        return resp

    # ---- Jobs ----
    @app.get("/api/jobs")
    def list_jobs():
        with SessionLocal() as db:
            rows = db.scalars(select(Job).order_by(Job.id.desc())).all()
            return jsonify({"jobs":[{"id":r.id,"title":r.title,"client":r.client,"status":r.status,"city":r.city,"code":r.code,"date":r.date,"note":r.note} for r in rows]})

    @app.post("/api/jobs")
    def create_job():
        j = request.get_json(force=True)
        with SessionLocal() as db:
            r = Job(title=j["title"], client=j["client"], status=j.get("status","Plán"), city=j["city"], code=j["code"], date=j["date"], note=j.get("note"))
            db.add(r); db.commit(); db.refresh(r)
            return jsonify({"id": r.id})

    @app.delete("/api/jobs")
    def delete_job():
        jid = int(request.args.get("id"))
        with SessionLocal() as db:
            db.execute(delete(Job).where(Job.id==jid))
            db.execute(delete(Material).where(Material.job_id==jid))
            db.execute(delete(Tool).where(Tool.job_id==jid))
            db.execute(delete(JobAssignment).where(JobAssignment.job_id==jid))
            db.execute(delete(Photo).where(Photo.job_id==jid))
            db.execute(delete(Timesheet).where(Timesheet.job_id==jid))
            db.commit()
        return jsonify({"ok": True})

    @app.get("/api/jobs/<int:jid>")
    def job_detail(jid:int):
        with SessionLocal() as db:
            j = db.get(Job, jid)
            if not j: return jsonify({"error":"Not found"}),404
            mats = db.scalars(select(Material).where(Material.job_id==jid)).all()
            tools = db.scalars(select(Tool).where(Tool.job_id==jid)).all()
            photos = db.scalars(select(Photo).where(Photo.job_id==jid)).all()
            assigns = db.scalars(select(JobAssignment.employee_id).where(JobAssignment.job_id==jid)).all()
            return jsonify({
                "job":{"id":j.id,"title":j.title,"client":j.client,"status":j.status,"city":j.city,"code":j.code,"date":j.date,"note":j.note},
                "materials":[{"id":m.id,"name":m.name,"qty":float(m.qty),"unit":m.unit} for m in mats],
                "tools":[{"id":t.id,"name":t.name,"qty":float(t.qty),"unit":t.unit} for t in tools],
                "photos":[{"id":p.id,"filename":p.filename} for p in photos],
                "assignments": list(assigns),
            })

    @app.post("/api/jobs/<int:jid>/materials")
    def add_material(jid:int):
        j = request.get_json(force=True)
        with SessionLocal() as db:
            m = Material(job_id=jid, name=j["name"], qty=j.get("qty",0), unit=j.get("unit","ks"))
            db.add(m); db.commit(); db.refresh(m)
            return jsonify({"id": m.id})

    @app.delete("/api/jobs/<int:jid>/materials")
    def delete_material(jid:int):
        mid = int(request.args.get("id"))
        with SessionLocal() as db:
            db.execute(delete(Material).where(Material.id==mid, Material.job_id==jid)); db.commit()
        return jsonify({"ok": True})

    @app.post("/api/jobs/<int:jid>/tools")
    def add_tool(jid:int):
        j = request.get_json(force=True)
        with SessionLocal() as db:
            t = Tool(job_id=jid, name=j["name"], qty=j.get("qty",0), unit=j.get("unit","ks"))
            db.add(t); db.commit(); db.refresh(t)
            return jsonify({"id": t.id})

    @app.delete("/api/jobs/<int:jid>/tools")
    def delete_tool(jid:int):
        tid = int(request.args.get("id"))
        with SessionLocal() as db:
            db.execute(delete(Tool).where(Tool.id==tid, Tool.job_id==jid)); db.commit()
        return jsonify({"ok": True})

    @app.post("/api/jobs/<int:jid>/assignments")
    def set_assignments(jid:int):
        j = request.get_json(force=True)
        ids = list({int(x) for x in j.get("employee_ids", [])})
        with SessionLocal() as db:
            db.execute(delete(JobAssignment).where(JobAssignment.job_id==jid))
            for eid in ids:
                db.add(JobAssignment(job_id=jid, employee_id=eid))
            db.commit()
        return jsonify({"ok": True})

    # photos: store to local uploads (ephemeral, but UI works)
    @app.post("/api/jobs/<int:jid>/photos")
    def add_photo(jid:int):
        j = request.get_json(force=True)
        data_url = j.get("data_url","")
        m = re.match(r"data:image/(png|jpeg);base64,(.+)", data_url)
        if not m:
            return jsonify({"error":"Bad image"}),400
        ext = "jpg" if m.group(1)=="jpeg" else "png"
        b = base64.b64decode(m.group(2))
        fname = f"{uuid.uuid4().hex}.{ext}"
        path = os.path.join("static","uploads",fname)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f: f.write(b)
        with SessionLocal() as db:
            p = Photo(job_id=jid, filename=fname); db.add(p); db.commit(); db.refresh(p)
            return jsonify({"id":p.id})

    # ---- Employees ----
    @app.get("/api/employees")
    def list_employees():
        with SessionLocal() as db:
            rows = db.scalars(select(Employee).order_by(Employee.id.desc())).all()
            return jsonify({"employees":[{"id":r.id,"name":r.name,"role":r.role} for r in rows]})

    @app.post("/api/employees")
    def create_employee():
        j = request.get_json(force=True)
        with SessionLocal() as db:
            e = Employee(name=j["name"], role=j.get("role","Zahradník"))
            db.add(e); db.commit(); db.refresh(e)
            return jsonify({"id": e.id})

    @app.delete("/api/employees")
    def delete_employee():
        eid = int(request.args.get("id"))
        with SessionLocal() as db:
            db.execute(delete(Employee).where(Employee.id==eid)); db.commit()
        return jsonify({"ok": True})

    # ---- Tasks ----
    @app.get("/api/tasks")
    def list_tasks():
        job_id = request.args.get("job_id")
        with SessionLocal() as db:
            q = select(Task).order_by(Task.id.desc())
            if job_id:
                q = q.where(Task.job_id==int(job_id))
            rows = db.scalars(q).all()
            return jsonify({"tasks":[{"id":r.id,"title":r.title,"description":r.description,"due_date":r.due_date,"employee_id":r.employee_id,"job_id":r.job_id,"status":r.status} for r in rows]})

    @app.post("/api/tasks")
    def create_task():
        j = request.get_json(force=True)
        with SessionLocal() as db:
            t = Task(title=j["title"], description=j.get("description"), due_date=j.get("due_date"), employee_id=(int(j["employee_id"]) if j.get("employee_id") else None), job_id=(int(j["job_id"]) if j.get("job_id") else None))
            db.add(t); db.commit(); db.refresh(t)
            return jsonify({"id": t.id})

    @app.patch("/api/tasks")
    def update_task():
        j = request.get_json(force=True)
        tid = int(j["id"])
        with SessionLocal() as db:
            db.execute(update(Task).where(Task.id==tid).values(status=j.get("status")))
            db.commit()
        return jsonify({"ok":True})

    @app.delete("/api/tasks")
    def delete_task():
        tid = int(request.args.get("id"))
        with SessionLocal() as db:
            db.execute(delete(Task).where(Task.id==tid)); db.commit()
        return jsonify({"ok": True})

    # ---- Timesheets ----
    @app.get("/api/timesheets")
    def list_timesheets():
        job_id = request.args.get("job_id")
        employee_id = request.args.get("employee_id")
        with SessionLocal() as db:
            q = select(Timesheet).order_by(Timesheet.id.desc())
            if job_id: q = q.where(Timesheet.job_id==int(job_id))
            if employee_id: q = q.where(Timesheet.employee_id==int(employee_id))
            rows = db.scalars(q).all()
            # join helpers
            job_map = {j.id:j.title for j in db.scalars(select(Job)).all()}
            emp_map = {e.id:e.name for e in db.scalars(select(Employee)).all()}
            return jsonify({"rows":[{"id":r.id,"job_id":r.job_id,"employee_id":r.employee_id,"employee_name":emp_map.get(r.employee_id),"job_title":job_map.get(r.job_id),"date":r.date,"hours":float(r.hours),"place":r.place,"activity":r.activity} for r in rows]})

    @app.post("/api/timesheets")
    def add_timesheet():
        j = request.get_json(force=True)
        with SessionLocal() as db:
            t = Timesheet(job_id=(int(j["job_id"]) if j.get("job_id") else None), employee_id=(int(j["employee_id"]) if j.get("employee_id") else None), date=j["date"], hours=float(j["hours"]), place=j.get("place"), activity=j.get("activity"))
            db.add(t); db.commit(); db.refresh(t)
            return jsonify({"id": t.id})

    @app.delete("/api/timesheets")
    def del_timesheet():
        tid = int(request.args.get("id"))
        with SessionLocal() as db:
            db.execute(delete(Timesheet).where(Timesheet.id==tid)); db.commit()
        return jsonify({"ok":True})

    # ---- Warehouse ----
    @app.get("/api/items")
    def list_items():
        site = request.args.get("site","lipnik")
        with SessionLocal() as db:
            rows = db.scalars(select(WarehouseItem).where(WarehouseItem.site==site).order_by(WarehouseItem.id.desc())).all()
            return jsonify({"items":[{"id":r.id,"category":r.category,"name":r.name,"qty":float(r.qty),"unit":r.unit} for r in rows]})

    @app.post("/api/items")
    def create_item():
        j = request.get_json(force=True)
        with SessionLocal() as db:
            it = WarehouseItem(site=j["site"], category=j["category"], name=j["name"], qty=float(j["qty"]), unit=j["unit"])
            db.add(it); db.commit(); db.refresh(it)
            return jsonify({"id": it.id})

    @app.delete("/api/items")
    def delete_item():
        iid = int(request.args.get("id"))
        with SessionLocal() as db:
            db.execute(delete(WarehouseItem).where(WarehouseItem.id==iid)); db.commit()
        return jsonify({"ok":True})

    # ---- Users (admin only endpoints kept simple) ----
    @app.get("/api/users")
    def list_users():
        with SessionLocal() as db:
            rows = db.scalars(select(User).order_by(User.id)).all()
            return jsonify({"users":[{"id":u.id,"email":u.email,"name":u.name,"role":u.role,"active":u.active} for u in rows]})

    @app.post("/api/users")
    def create_user():
        j = request.get_json(force=True)
        with SessionLocal() as db:
            u = User(email=j["email"].lower(), name=j["name"], role=j.get("role","worker"), password=j.get("password","changeme"), active=True)
            db.add(u); db.commit(); db.refresh(u)
            return jsonify({"id": u.id})

    @app.patch("/api/users")
    def update_user():
        j = request.get_json(force=True)
        uid = int(j["id"])
        values = {}
        if "role" in j: values["role"] = j["role"]
        if "active" in j: values["active"] = bool(j["active"])
        with SessionLocal() as db:
            db.execute(update(User).where(User.id==uid).values(**values)); db.commit()
        return jsonify({"ok":True})

    # ---- Export routes ----
    @app.get("/export/warehouse.xlsx")
    def export_warehouse():
        wb = Workbook(); ws = wb.active; ws.title = "Warehouse"
        ws.append(["ID","Site","Category","Name","Qty","Unit"])
        with SessionLocal() as db:
            for r in db.scalars(select(WarehouseItem).order_by(WarehouseItem.site, WarehouseItem.category, WarehouseItem.name)).all():
                ws.append([r.id, r.site, r.category, r.name, float(r.qty), r.unit])
        bio = io.BytesIO(); wb.save(bio); bio.seek(0)
        return send_file(bio, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="warehouse.xlsx")

    @app.get("/export/job_materials.xlsx")
    def export_job_materials():
        job_id = int(request.args.get("job_id"))
        wb = Workbook(); ws = wb.active; ws.title = "Materials"
        ws.append(["Name","Qty","Unit"])
        with SessionLocal() as db:
            for m in db.scalars(select(Material).where(Material.job_id==job_id)).all():
                ws.append([m.name, float(m.qty), m.unit])
        bio = io.BytesIO(); wb.save(bio); bio.seek(0)
        return send_file(bio, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="job_materials.xlsx")

    @app.get("/export/employee_hours.xlsx")
    def export_employee_hours():
        employee_id = int(request.args.get("employee_id"))
        wb = Workbook(); ws = wb.active; ws.title = "Hours"
        ws.append(["Date","Hours","Job","Place","Activity"])
        with SessionLocal() as db:
            job_map = {j.id:j.title for j in db.scalars(select(Job)).all()}
            for r in db.scalars(select(Timesheet).where(Timesheet.employee_id==employee_id).order_by(Timesheet.date)).all():
                ws.append([r.date, float(r.hours), job_map.get(r.job_id, ""), r.place or "", r.activity or ""])
        bio = io.BytesIO(); wb.save(bio); bio.seek(0)
        return send_file(bio, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="employee_hours.xlsx")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
