from pathlib import Path
from datetime import datetime
import csv

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app
)

from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from . import db
from .models import (
    User,
    LeaveRequest,
    SOP,
    Appraisal,
    Audit,
    Holiday,
    CommonURL,
    Training,
    SyncLog
)


admin_bp = Blueprint("head", __name__)


# =========================================================
# DEPARTMENT HEAD ACCESS PROTECTION
# =========================================================

@admin_bp.before_request
@login_required
def protect():

    if current_user.role != "head":

        flash(
            "Only department heads can access this section.",
            "danger"
        )

        return redirect(
            url_for("main.dashboard")
        )


# =========================================================
# DEPARTMENT HEAD DASHBOARD
# =========================================================

@admin_bp.route("/")
def dashboard():

    pending = (
        LeaveRequest.query
        .filter_by(
            department=current_user.department,
            status="Pending"
        )
        .order_by(
            LeaveRequest.created_at.desc()
        )
        .all()
    )

    employees = (
        User.query
        .filter_by(
            department=current_user.department,
            role="employee"
        )
        .all()
    )

    appraisals = (
        Appraisal.query
        .filter_by(
            department=current_user.department
        )
        .order_by(
            Appraisal.created_at.desc()
        )
        .all()
    )

    audits = (
        Audit.query
        .filter_by(
            department=current_user.department
        )
        .order_by(
            Audit.audit_date
        )
        .all()
    )

    sops = (
        SOP.query
        .filter_by(
            department=current_user.department
        )
        .order_by(
            SOP.uploaded_at.desc()
        )
        .all()
    )

    holidays = (
        Holiday.query
        .order_by(
            Holiday.date
        )
        .all()
    )

    sync_logs = (
        SyncLog.query
        .order_by(
            SyncLog.synced_at.desc()
        )
        .limit(8)
        .all()
    )

    return render_template(
        "head.html",
        pending=pending,
        employees=employees,
        appraisals=appraisals,
        audits=audits,
        sops=sops,
        holidays=holidays,
        sync_logs=sync_logs
    )


# =========================================================
# LEAVE APPROVAL / REJECTION
# =========================================================

@admin_bp.route(
    "/leave/<int:id>/<action>",
    methods=["POST"]
)
def leave_action(id, action):

    req = db.session.get(
        LeaveRequest,
        id
    )

    if (
        not req
        or req.department != current_user.department
        or req.status != "Pending"
    ):

        flash(
            "This request is not available to you.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    employee = (
        User.query
        .filter_by(
            employee_id=req.employee_id
        )
        .first()
    )

    if not employee:

        flash(
            "Employee record could not be found.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    req.head_comment = (
        request.form
        .get("comment", "")
        .strip()
    )

    # -----------------------------------------------------
    # APPROVE
    # -----------------------------------------------------

    if action == "approve":

        # Paid leave
        if req.leave_type == "Paid":

            remaining = (
                employee.paid_leave_limit
                - employee.paid_leave_used
            )

            if req.days > remaining:

                flash(
                    "Approval blocked: employee does not have enough paid leave.",
                    "danger"
                )

                return redirect(
                    url_for("head.dashboard")
                )

            employee.paid_leave_used += req.days

        # Unpaid leave
        else:

            remaining = (
                employee.total_leave
                - employee.paid_leave_used
                - employee.unpaid_leave_used
            )

            if req.days > remaining:

                flash(
                    "Approval blocked: employee does not have enough total leave.",
                    "danger"
                )

                return redirect(
                    url_for("head.dashboard")
                )

            employee.unpaid_leave_used += req.days

        req.status = "Approved"

    # -----------------------------------------------------
    # REJECT
    # -----------------------------------------------------

    elif action == "reject":

        req.status = "Rejected"

    else:

        flash(
            "Invalid leave action.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    db.session.commit()

    flash(
        f"Leave request {req.status.lower()}.",
        "success"
    )

    return redirect(
        url_for("head.dashboard")
    )


# =========================================================
# UPLOAD SOP
# =========================================================

@admin_bp.route(
    "/upload-sop",
    methods=["POST"]
)
def upload_sop():

    f = request.files.get("file")

    if not f or not f.filename:

        flash(
            "Choose an SOP file.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    filename = secure_filename(
        f.filename
    )

    if not filename:

        flash(
            "Invalid file name.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    upload_folder = Path(
        current_app.config["UPLOAD_FOLDER"]
    )

    upload_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    path = upload_folder / filename

    f.save(path)

    sop = SOP(
        name=filename,
        department=current_user.department,
        version=request.form.get(
            "version",
            "1.0"
        ),
        code=request.form.get(
            "code",
            ""
        ),
        filename=filename,
        uploaded_by=current_user.name
    )

    db.session.add(sop)
    db.session.commit()

    flash(
        "SOP uploaded for your department.",
        "success"
    )

    return redirect(
        url_for("head.dashboard")
    )


# =========================================================
# ADD AUDIT
# =========================================================

@admin_bp.route(
    "/add-audit",
    methods=["POST"]
)
def add_audit():

    # -----------------------------------------------------
    # READ AND VALIDATE DATES
    # -----------------------------------------------------

    try:

        audit_date = datetime.strptime(
            request.form["audit_date"],
            "%Y-%m-%d"
        ).date()

        next_date = (
            datetime.strptime(
                request.form["next_audit_date"],
                "%Y-%m-%d"
            ).date()
            if request.form.get(
                "next_audit_date"
            )
            else None
        )

    except (ValueError, KeyError):

        flash(
            "Invalid audit date.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    # -----------------------------------------------------
    # VALIDATE AUDIT TYPE
    # -----------------------------------------------------

    audit_type = (
        request.form
        .get("audit_type", "")
        .strip()
    )

    if audit_type not in (
        "ISO",
        "GDP"
    ):

        flash(
            "Audit type must be ISO or GDP.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    # -----------------------------------------------------
    # READ FORM DATA
    # -----------------------------------------------------

    name = (
        request.form
        .get("name", "")
        .strip()
    )

    auditor = (
        request.form
        .get("auditor", "")
        .strip()
    )

    if not name:

        flash(
            "Audit name is required.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    # -----------------------------------------------------
    # SAVE TO DATABASE
    # -----------------------------------------------------

    audit = Audit(
        name=name,
        department=current_user.department,
        audit_type=audit_type,
        auditor=auditor,
        audit_date=audit_date,
        next_audit_date=next_date,
        status="Upcoming"
    )

    db.session.add(audit)
    db.session.commit()

    # -----------------------------------------------------
    # ALSO SAVE TO CSV
    #
    # This is important because sync.py rebuilds the Audit
    # table from audits.csv.
    # -----------------------------------------------------

    csv_path = (
        Path(
            current_app.config["DATA_FOLDER"]
        )
        / "audits.csv"
    )

    csv_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fieldnames = [
        "name",
        "department",
        "audit_type",
        "auditor",
        "audit_date",
        "next_audit_date",
        "status"
    ]

    file_exists = (
        csv_path.exists()
        and csv_path.stat().st_size > 0
    )

    with csv_path.open(
        "a",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        if not file_exists:

            writer.writeheader()

        writer.writerow({
            "name": name,
            "department": current_user.department,
            "audit_type": audit_type,
            "auditor": auditor,
            "audit_date": audit_date.isoformat(),
            "next_audit_date": (
                next_date.isoformat()
                if next_date
                else ""
            ),
            "status": "Upcoming"
        })

    flash(
        "Audit date added.",
        "success"
    )

    return redirect(
        url_for("head.dashboard")
    )


# =========================================================
# ADD HOLIDAY
# =========================================================

@admin_bp.route(
    "/add-holiday",
    methods=["POST"]
)
def add_holiday():

    try:

        d = datetime.strptime(
            request.form["date"],
            "%Y-%m-%d"
        ).date()

    except (ValueError, KeyError):

        flash(
            "Invalid holiday date.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    name = (
        request.form
        .get("name", "")
        .strip()
    )

    if not name:

        flash(
            "Holiday name is required.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    holiday_type = (
        request.form
        .get(
            "holiday_type",
            "Company"
        )
        .strip()
    )

    db.session.add(
        Holiday(
            name=name,
            date=d,
            holiday_type=holiday_type
        )
    )

    db.session.commit()

    flash(
        "Holiday added to the calendar.",
        "success"
    )

    return redirect(
        url_for("head.dashboard")
    )


# =========================================================
# RAISE APPRAISAL
# =========================================================

@admin_bp.route(
    "/raise-appraisal",
    methods=["POST"]
)
def raise_appraisal():

    try:

        employee_id = int(
            request.form["employee_id"]
        )

    except (ValueError, KeyError):

        flash(
            "Invalid employee selected.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    employee = db.session.get(
        User,
        employee_id
    )

    if (
        not employee
        or employee.department != current_user.department
        or employee.role != "employee"
    ):

        flash(
            "You can only raise an appraisal for an employee in your department.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    cycle = (
        request.form
        .get("cycle", "")
        .strip()
    )

    if not cycle:

        flash(
            "Appraisal cycle is required.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    next_date = None

    if request.form.get("next_date"):

        try:

            next_date = datetime.strptime(
                request.form["next_date"],
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Invalid appraisal date.",
                "danger"
            )

            return redirect(
                url_for("head.dashboard")
            )

    appraisal = Appraisal(
        employee_id=employee.employee_id,
        department=employee.department,
        cycle=cycle,
        stage="Raised",
        completion=10,
        next_date=next_date,
        raised_by=current_user.name
    )

    db.session.add(appraisal)
    db.session.commit()

    flash(
        "Appraisal raised.",
        "success"
    )

    return redirect(
        url_for("head.dashboard")
    )
