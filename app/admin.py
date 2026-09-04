
from pathlib import Path
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from . import db
from .models import User, LeaveRequest, SOP, Appraisal, Audit, Holiday, CommonURL, Training, SyncLog

admin_bp = Blueprint("head", __name__)

@admin_bp.before_request
@login_required
def protect():
    if current_user.role != "head":
        flash("Only department heads can access this section.", "danger")
        return redirect(url_for("main.dashboard"))

@admin_bp.route("/")
def dashboard():
    pending = LeaveRequest.query.filter_by(department=current_user.department, status="Pending").order_by(LeaveRequest.created_at.desc()).all()
    employees = User.query.filter_by(department=current_user.department, role="employee").all()
    appraisals = Appraisal.query.filter_by(department=current_user.department).order_by(Appraisal.created_at.desc()).all()
    audits = Audit.query.filter_by(department=current_user.department).order_by(Audit.audit_date).all()
    sops = SOP.query.filter_by(department=current_user.department).order_by(SOP.uploaded_at.desc()).all()
    return render_template("head.html", pending=pending, employees=employees, appraisals=appraisals,
                           audits=audits, sops=sops, holidays=Holiday.query.order_by(Holiday.date).all(),
                           sync_logs=SyncLog.query.order_by(SyncLog.synced_at.desc()).limit(8).all())

@admin_bp.route("/leave/<int:id>/<action>", methods=["POST"])
def leave_action(id, action):
    req = db.session.get(LeaveRequest, id)
    if not req or req.department != current_user.department or req.status != "Pending":
        flash("This request is not available to you.", "danger")
        return redirect(url_for("head.dashboard"))
    employee = User.query.filter_by(employee_id=req.employee_id).first()
    req.head_comment = request.form.get("comment","").strip()
    if action == "approve":
        if req.leave_type == "Paid":
            remaining = employee.paid_leave_limit - employee.paid_leave_used
            if req.days > remaining:
                flash("Approval blocked: employee does not have enough paid leave.", "danger")
                return redirect(url_for("head.dashboard"))
            employee.paid_leave_used += req.days
        else:
            remaining = employee.total_leave - employee.paid_leave_used - employee.unpaid_leave_used
            if req.days > remaining:
                flash("Approval blocked: employee does not have enough total leave.", "danger")
                return redirect(url_for("head.dashboard"))
            employee.unpaid_leave_used += req.days
        req.status = "Approved"
    else:
        req.status = "Rejected"
    db.session.commit()
    flash(f"Leave request {req.status.lower()}.", "success")
    return redirect(url_for("head.dashboard"))

@admin_bp.route("/upload-sop", methods=["POST"])
def upload_sop():
    f = request.files.get("file")
    if not f or not f.filename:
        flash("Choose an SOP file.", "danger")
        return redirect(url_for("head.dashboard"))
    filename = secure_filename(f.filename)
    path = Path(current_app.config["UPLOAD_FOLDER"]) / filename
    f.save(path)
    db.session.add(SOP(name=filename, department=current_user.department,
                       version=request.form.get("version","1.0"),
                       code=request.form.get("code",""), filename=filename,
                       uploaded_by=current_user.name))
    db.session.commit()
    flash("SOP uploaded for your department.", "success")
    return redirect(url_for("head.dashboard"))

@admin_bp.route("/add-audit", methods=["POST"])
def add_audit():
    try:
        audit_date = datetime.strptime(request.form["audit_date"], "%Y-%m-%d").date()
        next_date = datetime.strptime(request.form["next_audit_date"], "%Y-%m-%d").date() if request.form.get("next_audit_date") else None
    except ValueError:
        flash("Invalid audit date.", "danger")
        return redirect(url_for("head.dashboard"))
    audit_type = request.form["audit_type"]
    if audit_type not in ("ISO", "GDP"):
        flash("Audit type must be ISO or GDP.", "danger")
        return redirect(url_for("head.dashboard"))
    db.session.add(Audit(name=request.form["name"], department=current_user.department,
                          audit_type=audit_type, auditor=request.form.get("auditor",""),
                          audit_date=audit_date, next_audit_date=next_date, status="Upcoming"))
    db.session.commit()
    flash("Audit date added.", "success")
    return redirect(url_for("head.dashboard"))

@admin_bp.route("/add-holiday", methods=["POST"])
def add_holiday():
    try:
        d = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid holiday date.", "danger")
        return redirect(url_for("head.dashboard"))
    db.session.add(Holiday(name=request.form["name"], date=d, holiday_type=request.form.get("holiday_type","Company")))
    db.session.commit()
    flash("Holiday added to the calendar.", "success")
    return redirect(url_for("head.dashboard"))

@admin_bp.route("/raise-appraisal", methods=["POST"])
def raise_appraisal():
    employee = db.session.get(User, int(request.form["employee_id"]))
    if not employee or employee.department != current_user.department or employee.role != "employee":
        flash("You can only raise an appraisal for an employee in your department.", "danger")
        return redirect(url_for("head.dashboard"))
    db.session.add(Appraisal(employee_id=employee.employee_id, department=employee.department,
                             cycle=request.form["cycle"], stage="Raised", completion=10,
                             next_date=datetime.strptime(request.form["next_date"], "%Y-%m-%d").date() if request.form.get("next_date") else None,
                             raised_by=current_user.name))
    db.session.commit()
    flash("Appraisal raised.", "success")
    return redirect(url_for("head.dashboard"))
