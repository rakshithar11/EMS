from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from pathlib import Path
from datetime import datetime

from . import db
from .models import (
    User,
    LeaveRequest,
    Appraisal,
    SOP,
    Audit,
    Holiday,
    Training,
)

admin_bp = Blueprint("admin", __name__)


# ============================================================
# ACCESS CONTROL
# ============================================================

def protect():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    if current_user.role not in ("head", "admin"):
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("main.dashboard"))

    return None


# ============================================================
# HEAD / ADMIN DASHBOARD
# ============================================================

@admin_bp.route("/")
@login_required
def dashboard():

    blocked = protect()
    if blocked:
        return blocked

    if current_user.role == "admin":

        pending = (
            LeaveRequest.query
            .filter_by(status="Pending")
            .order_by(LeaveRequest.created_at.desc())
            .all()
        )

        employees = (
            User.query
            .filter_by(role="employee")
            .order_by(User.name)
            .all()
        )

        appraisals = (
            Appraisal.query
            .order_by(Appraisal.created_at.desc())
            .all()
        )

        audits = (
            Audit.query
            .order_by(Audit.audit_date)
            .all()
        )

        sops = (
            SOP.query
            .order_by(SOP.created_at.desc())
            .all()
        )

        trainings = (
            Training.query
            .order_by(Training.uploaded_at.desc())
            .all()
        )

    else:

        pending = (
            LeaveRequest.query
            .filter(
                LeaveRequest.forwarded_to == current_user.email,
                LeaveRequest.status == "Pending"
            )
            .order_by(LeaveRequest.created_at.desc())
            .all()
        )

        employees = (
            User.query
            .filter(
                User.role == "employee",
                User.department == current_user.department
            )
            .order_by(User.name)
            .all()
        )

        appraisals = (
            Appraisal.query
            .filter_by(department=current_user.department)
            .order_by(Appraisal.created_at.desc())
            .all()
        )

        audits = (
            Audit.query
            .filter_by(department=current_user.department)
            .order_by(Audit.audit_date)
            .all()
        )

        sops = (
            SOP.query
            .filter_by(department=current_user.department)
            .order_by(SOP.created_at.desc())
            .all()
        )

        trainings = (
            Training.query
            .filter(
                (Training.department == current_user.department) |
                (Training.department.is_(None)) |
                (Training.department == "")
            )
            .order_by(Training.uploaded_at.desc())
            .all()
        )

    return render_template(
        "head.html",
        pending=pending,
        employees=employees,
        appraisals=appraisals,
        audits=audits,
        sops=sops,
        trainings=trainings,
    )


# ============================================================
# LEAVE REQUEST ACTION
# ============================================================

@admin_bp.route("/leave/<int:leave_id>/<action>", methods=["POST"])
@login_required
def leave_action(leave_id, action):

    blocked = protect()
    if blocked:
        return blocked

    leave = db.session.get(LeaveRequest, leave_id)

    if not leave:
        flash("Leave request not found.", "danger")
        return redirect(url_for("admin.dashboard"))

    if leave.status != "Pending":
        flash("This leave request has already been processed.", "warning")
        return redirect(url_for("admin.dashboard"))

    # Regular department heads can only process requests
    # specifically forwarded to them.
    if current_user.role == "head":
        if leave.forwarded_to != current_user.email:
            flash(
                "This leave request was not forwarded to you.",
                "danger"
            )
            return redirect(url_for("admin.dashboard"))

    if action == "approve":

        employee = db.session.get(User, leave.user_id)

        if not employee:
            flash("Employee not found.", "danger")
            return redirect(url_for("admin.dashboard"))

        days = leave.days

        # Re-check balances before approval.
        if days <= 0:
            flash("Invalid leave duration.", "danger")
            return redirect(url_for("admin.dashboard"))

        total_used = (
            employee.paid_leave_used +
            employee.unpaid_leave_used
        )

        remaining_total = employee.total_leave - total_used

        if days > remaining_total:
            flash(
                "Leave cannot be approved because the employee "
                "does not have enough total leave balance.",
                "danger"
            )
            return redirect(url_for("admin.dashboard"))

        if leave.leave_type == "Paid":

            remaining_paid = (
                employee.paid_leave_limit -
                employee.paid_leave_used
            )

            if days > remaining_paid:
                flash(
                    "Leave cannot be approved because the employee "
                    "does not have enough paid leave balance.",
                    "danger"
                )
                return redirect(url_for("admin.dashboard"))

            employee.paid_leave_used += days

        else:
            employee.unpaid_leave_used += days

        leave.status = "Approved"

        flash(
            f"Leave request from {employee.name} approved.",
            "success"
        )

    elif action == "reject":

        leave.status = "Rejected"

        flash(
            "Leave request rejected.",
            "success"
        )

    else:
        flash("Invalid action.", "danger")
        return redirect(url_for("admin.dashboard"))

    db.session.commit()

    return redirect(url_for("admin.dashboard"))


# ============================================================
# SOP UPLOAD
# ============================================================

@admin_bp.route("/upload-sop", methods=["POST"])
@login_required
def upload_sop():

    blocked = protect()
    if blocked:
        return blocked

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    version = request.form.get("version", "").strip()

    if current_user.role == "admin":
        department = request.form.get("department", "").strip()
    else:
        department = current_user.department

    file = request.files.get("file")

    if not title:
        flash("Please enter an SOP title.", "danger")
        return redirect(url_for("admin.dashboard"))

    if not file or not file.filename:
        flash("Please select an SOP PDF file.", "danger")
        return redirect(url_for("admin.dashboard"))

    original_name = secure_filename(file.filename)

    if not original_name:
        flash("Invalid file name.", "danger")
        return redirect(url_for("admin.dashboard"))

    extension = Path(original_name).suffix.lower()

    if extension != ".pdf":
        flash("SOP files must be PDF files.", "danger")
        return redirect(url_for("admin.dashboard"))

    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)

    filename = (
        f"sop_{datetime.now().strftime('%Y%m%d%H%M%S')}_"
        f"{original_name}"
    )

    file.save(upload_folder / filename)

    sop = SOP(
        title=title,
        department=department,
        description=description,
        version=version,
        filename=filename,
    )

    db.session.add(sop)
    db.session.commit()

    flash("SOP uploaded successfully.", "success")

    return redirect(url_for("admin.dashboard"))


# ============================================================
# TRAINING UPLOAD
# ============================================================

@admin_bp.route("/upload-training", methods=["POST"])
@login_required
def upload_training():

    blocked = protect()
    if blocked:
        return blocked

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if current_user.role == "admin":
        department = request.form.get("department", "").strip()
    else:
        department = current_user.department

    file = request.files.get("file")

    if not title:
        flash("Please enter a training title.", "danger")
        return redirect(url_for("admin.dashboard"))

    if not file or not file.filename:
        flash("Please select a training file.", "danger")
        return redirect(url_for("admin.dashboard"))

    original_name = secure_filename(file.filename)

    if not original_name:
        flash("Invalid file name.", "danger")
        return redirect(url_for("admin.dashboard"))

    extension = Path(original_name).suffix.lower()

    allowed_extensions = {
        ".pdf",
        ".mp4",
        ".webm",
        ".ogg",
        ".mov",
        ".avi",
        ".mkv",
    }

    if extension not in allowed_extensions:
        flash(
            "Training files must be PDF or video files "
            "(MP4, WebM, OGG, MOV, AVI, or MKV).",
            "danger"
        )
        return redirect(url_for("admin.dashboard"))

    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)

    filename = (
        f"training_{datetime.now().strftime('%Y%m%d%H%M%S')}_"
        f"{original_name}"
    )

    file.save(upload_folder / filename)

    training = Training(
        title=title,
        department=department,
        description=description,
        filename=filename,
        uploaded_by=current_user.name,
        uploaded_at=datetime.utcnow(),
    )

    db.session.add(training)
    db.session.commit()

    flash("Training material uploaded successfully.", "success")

    return redirect(url_for("admin.dashboard"))


# ============================================================
# ADD AUDIT
# ============================================================

@admin_bp.route("/add-audit", methods=["POST"])
@login_required
def add_audit():

    blocked = protect()
    if blocked:
        return blocked

    name = request.form.get("name", "").strip()
    audit_type = request.form.get("audit_type", "").strip()
    auditor = request.form.get("auditor", "").strip()
    audit_date_text = request.form.get("audit_date", "").strip()
    next_audit_date_text = request.form.get(
        "next_audit_date",
        ""
    ).strip()
    status = request.form.get("status", "Upcoming").strip()

    if current_user.role == "admin":
        department = request.form.get("department", "").strip()
    else:
        department = current_user.department

    if not name or not audit_date_text:
        flash(
            "Audit name and audit date are required.",
            "danger"
        )
        return redirect(url_for("admin.dashboard"))

    try:
        audit_date = datetime.strptime(
            audit_date_text,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        flash("Invalid audit date.", "danger")
        return redirect(url_for("admin.dashboard"))

    next_audit_date = None

    if next_audit_date_text:
        try:
            next_audit_date = datetime.strptime(
                next_audit_date_text,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            flash("Invalid next audit date.", "danger")
            return redirect(url_for("admin.dashboard"))

    audit = Audit(
        name=name,
        department=department,
        audit_type=audit_type,
        auditor=auditor,
        audit_date=audit_date,
        next_audit_date=next_audit_date,
        status=status,
    )

    db.session.add(audit)

    # Keep audit information in the CSV source as well,
    # because sync.py rebuilds audit records from the CSV.
    csv_path = (
        Path(current_app.config["DATA_FOLDER"]) /
        "audits.csv"
    )

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    import csv

    file_exists = csv_path.exists()

    with open(
        csv_path,
        "a",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "name",
                "department",
                "audit_type",
                "auditor",
                "audit_date",
                "next_audit_date",
                "status",
            ])

        writer.writerow([
            name,
            department,
            audit_type,
            auditor,
            audit_date.isoformat(),
            next_audit_date.isoformat()
            if next_audit_date else "",
            status,
        ])

    db.session.commit()

    flash("Audit added successfully.", "success")

    return redirect(url_for("admin.dashboard"))


# ============================================================
# ADD HOLIDAY
# ============================================================

@admin_bp.route("/add-holiday", methods=["POST"])
@login_required
def add_holiday():

    blocked = protect()
    if blocked:
        return blocked

    name = request.form.get("name", "").strip()
    date_text = request.form.get("date", "").strip()

    if not name or not date_text:
        flash(
            "Holiday name and date are required.",
            "danger"
        )
        return redirect(url_for("admin.dashboard"))

    try:
        holiday_date = datetime.strptime(
            date_text,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        flash("Invalid holiday date.", "danger")
        return redirect(url_for("admin.dashboard"))

    holiday = Holiday(
        name=name,
        date=holiday_date,
    )

    db.session.add(holiday)
    db.session.commit()

    flash("Holiday added successfully.", "success")

    return redirect(url_for("admin.dashboard"))


# ============================================================
# RAISE APPRAISAL
# ============================================================

@admin_bp.route("/raise-appraisal", methods=["POST"])
@login_required
def raise_appraisal():

    blocked = protect()
    if blocked:
        return blocked

    employee_id = request.form.get("employee_id", "").strip()
    cycle = request.form.get("cycle", "").strip()
    status = request.form.get("status", "Pending").strip()
    comments = request.form.get("comments", "").strip()

    employee = User.query.filter_by(
        employee_id=employee_id
    ).first()

    if not employee:
        flash("Employee not found.", "danger")
        return redirect(url_for("admin.dashboard"))

    # Regular heads can only raise appraisals
    # for employees in their own department.
    if current_user.role == "head":

        if employee.department != current_user.department:
            flash(
                "You can only raise appraisals for employees "
                "in your department.",
                "danger"
            )
            return redirect(url_for("admin.dashboard"))

    if not cycle:
        flash("Please enter an appraisal cycle.", "danger")
        return redirect(url_for("admin.dashboard"))

    appraisal = Appraisal(
        employee_id=employee.id,
        employee_name=employee.name,
        department=employee.department,
        cycle=cycle,
        status=status,
        comments=comments,
    )

    db.session.add(appraisal)
    db.session.commit()

    flash(
        f"Appraisal raised for {employee.name}.",
        "success"
    )

    return redirect(url_for("admin.dashboard"))
