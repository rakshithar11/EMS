
from pathlib import Path
from datetime import datetime
import csv
from . import db
from .models import Holiday, Department, CommonURL, Audit, Training

def _read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def sync_data_files():
    from flask import current_app
    if current_app.config.get("_sync_running"):
        return
    current_app.config["_sync_running"] = True
    try:
        data = Path(current_app.config["DATA_FOLDER"])

        # Common URLs
        p = data / "common_urls.csv"
        if p.exists():
            rows = _read_csv(p)
            CommonURL.query.delete()
            for r in rows:
                if r.get("name") and r.get("url"):
                    db.session.add(CommonURL(
                        name=r["name"].strip(), description=r.get("description","").strip(),
                        category=r.get("category","").strip(), department=r.get("department","").strip(),
                        url=r["url"].strip()
                    ))

        # Departments / department heads
        p = data / "departments.csv"
        if p.exists():
            rows = _read_csv(p)
            Department.query.delete()
            for r in rows:
                if r.get("name"):
                    db.session.add(Department(
                        name=r["name"].strip(), head_name=r.get("head_name","").strip(),
                        designation=r.get("designation","").strip(), email=r.get("email","").strip(),
                        phone=r.get("phone","").strip(), extension=r.get("extension","").strip(),
                        office=r.get("office","").strip(), floor=r.get("floor","").strip(),
                        room=r.get("room","").strip(), description=r.get("description","").strip()
                    ))

        # Holidays
        p = data / "holidays.csv"
        if p.exists():
            rows = _read_csv(p)
            Holiday.query.delete()
            for r in rows:
                if r.get("name") and r.get("date"):
                    d = datetime.strptime(r["date"].strip(), "%Y-%m-%d").date()
                    db.session.add(Holiday(name=r["name"].strip(), date=d,
                                           holiday_type=r.get("holiday_type","Company").strip()))

        # Audits (ISO/GDP)
        p = data / "audits.csv"
        if p.exists():
            rows = _read_csv(p)
            Audit.query.delete()
            for r in rows:
                if r.get("name"):
                    def dt(key):
                        v = r.get(key,"").strip()
                        return datetime.strptime(v, "%Y-%m-%d").date() if v else None
                    db.session.add(Audit(
                        name=r["name"].strip(), department=r.get("department","").strip(),
                        audit_type=r.get("audit_type","").strip(), auditor=r.get("auditor","").strip(),
                        audit_date=dt("audit_date"), next_audit_date=dt("next_audit_date"),
                        status=r.get("status","Upcoming").strip()
                    ))

        # Training catalog
        p = data / "training.csv"
        if p.exists():
            rows = _read_csv(p)
            Training.query.delete()
            for r in rows:
                if r.get("title"):
                    db.session.add(Training(
                        title=r["title"].strip(), description=r.get("description","").strip(),
                        department=r.get("department","").strip(), duration=r.get("duration","").strip(),
                        mandatory=r.get("mandatory","No").strip().lower() in ("yes","true","1"),
                        url=r.get("url","").strip()
                    ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Keep the previous database state if an editable file is malformed.
    finally:
        current_app.config["_sync_running"] = False
