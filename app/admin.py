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
    current_app,
    abort
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
    SyncLog,
    Event,
    EventPhoto
)


admin_bp = Blueprint("head", __name__)


# =========================================================
# DEPARTMENT HEAD / ADMIN ACCESS
# =========================================================

@admin_bp.before_request
@login_required
def protect():

    if current_user.role not in ("head", "admin"):

        flash(
            "You do not have permission to access this section.",
            "danger"
        )

        return redirect(
            url_for("main.dashboard")
        )


# =========================================================
# DEPARTMENT HEAD / ADMIN DASHBOARD
# =========================================================

@admin_bp.route("/")
def dashboard():

    # -----------------------------------------------------
    # ADMIN / GENERAL MANAGER
    #
    # Can see ALL pending leave requests.
    # -----------------------------------------------------

    if current_user.role == "admin":

        pending = (
            LeaveRequest.query
            .filter(
                LeaveRequest.status == "Pending"
            )
            .order_by(
                LeaveRequest.created_at.desc()
            )
            .all()
        )

        employees = (
            User.query
            .filter_by(
                role="employee"
            )
            .order_by(
                User.department,
                User.name
            )
            .all()
        )

        appraisals = (
            Appraisal.query
            .order_by(
                Appraisal.created_at.desc()
            )
            .all()
        )

        audits = (
            Audit.query
            .order_by(
                Audit.audit_date
            )
            .all()
        )

        sops = (
            SOP.query
            .order_by(
                SOP.uploaded_at.desc()
            )
            .all()
        )

        trainings = (
            Training.query
            .order_by(
                Training.uploaded_at.desc()
            )
            .all()
        )

    # -----------------------------------------------------
    # REGULAR DEPARTMENT HEAD
    #
    # Can see requests specifically forwarded to them and
    # manages only their own department's records.
    # -----------------------------------------------------

    else:

        pending = (
            LeaveRequest.query
            .filter(
                LeaveRequest.forwarded_to
                == current_user.email,

                LeaveRequest.status
                == "Pending"
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
            .order_by(
                User.name
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

        trainings = (
            Training.query
            .filter(
                (Training.department == current_user.department) |
                (Training.department.is_(None)) |
                (Training.department == "")
            )
            .order_by(
                Training.uploaded_at.desc()
            )
            .all()
        )

    # -----------------------------------------------------
    # NEW
    # Attach the default paid/unpaid split for each pending
    # request so the approval form can pre-fill it (the head
    # can still edit it before approving). This mirrors the
    # employee's originally requested type but is expressed
    # in chargeable days, i.e. with holidays already excluded.
    #
    # This loop only sets per-request display attributes — it
    # must NOT contain any of the queries above, or those
    # queries silently stop running whenever `pending` is
    # empty (which is exactly when a head has no pending
    # leave requests to approve).
    # -----------------------------------------------------

    for req in pending:

        chargeable = (
            req.chargeable_days
            if req.chargeable_days is not None
            else req.days
        )

        req.default_paid_days = (
            chargeable if req.leave_type == "Paid" else 0
        )

        req.default_unpaid_days = (
            chargeable if req.leave_type != "Paid" else 0
        )

        req.chargeable_display = chargeable

    # -----------------------------------------------------
    # COMMON DATA
    # -----------------------------------------------------

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

    # Events are visible to every head, and every head (not
    # just the admin) gets the "add event" / "upload photos"
    # forms in the template.
    events = (
        Event.query
        .order_by(
            Event.event_date.desc()
        )
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
        holidays=holidays,
        sync_logs=sync_logs,
        events=events
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

    if not req:

        flash(
            "Leave request could not be found.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    # -----------------------------------------------------
    # REGULAR HEAD
    #
    # Only the selected recipient can approve/reject.
    # -----------------------------------------------------

    if current_user.role == "head":

        if req.forwarded_to != current_user.email:

            flash(
                "This request was not forwarded to you.",
                "danger"
            )

            return redirect(
                url_for("head.dashboard")
            )

    # -----------------------------------------------------
    # ADMIN / GM
    #
    # Can approve/reject requests from ALL departments.
    # -----------------------------------------------------

    if req.status != "Pending":

        flash(
            "This request has already been processed.",
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
        .get(
            "comment",
            ""
        )
        .strip()
    )

    # =====================================================
    # APPROVE
    #
    # The approving head can split the chargeable days
    # between paid and unpaid instead of it being forced to
    # match whatever the employee originally selected.
    #
    # chargeable_days already has company holidays in the
    # requested range excluded, so that's what paid_days +
    # unpaid_days must add up to — not the raw calendar span.
    # =====================================================

    if action == "approve":

        required_days = (
            req.chargeable_days
            if req.chargeable_days is not None
            else req.days
        )

        paid_days_raw = request.form.get("paid_days")
        unpaid_days_raw = request.form.get("unpaid_days")

        if paid_days_raw is None and unpaid_days_raw is None:

            # No split was submitted — fall back to the
            # employee's originally requested type, unchanged.

            if req.leave_type == "Paid":
                paid_days, unpaid_days = required_days, 0
            else:
                paid_days, unpaid_days = 0, required_days

        else:

            try:
                paid_days = int(paid_days_raw or 0)
                unpaid_days = int(unpaid_days_raw or 0)

            except ValueError:

                flash(
                    "Paid/unpaid day split must be whole numbers.",
                    "danger"
                )

                return redirect(
                    url_for("head.dashboard")
                )

        if paid_days < 0 or unpaid_days < 0:

            flash(
                "Paid/unpaid days cannot be negative.",
                "danger"
            )

            return redirect(
                url_for("head.dashboard")
            )

        if paid_days + unpaid_days != required_days:

            flash(
                f"Paid + unpaid days must add up to "
                f"{required_days} chargeable day(s) "
                f"({req.holiday_days or 0} holiday day(s) "
                f"already excluded).",
                "danger"
            )

            return redirect(
                url_for("head.dashboard")
            )

        paid_remaining = (
            employee.paid_leave_limit
            - employee.paid_leave_used
        )

        if paid_days > paid_remaining:

            flash(
                "Approval blocked: employee only has "
                f"{paid_remaining} paid leave day(s) remaining.",
                "danger"
            )

            return redirect(
                url_for("head.dashboard")
            )

        total_remaining = (
            employee.total_leave
            - employee.paid_leave_used
            - employee.unpaid_leave_used
        )

        if (paid_days + unpaid_days) > total_remaining:

            flash(
                "Approval blocked: employee only has "
                f"{total_remaining} total leave day(s) remaining.",
                "danger"
            )

            return redirect(
                url_for("head.dashboard")
            )

        employee.paid_leave_used += paid_days
        employee.unpaid_leave_used += unpaid_days

        req.approved_paid_days = paid_days
        req.approved_unpaid_days = unpaid_days
        req.status = "Approved"

    # =====================================================
    # REJECT
    # =====================================================

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

    db.session.add(
        SOP(
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
    )

    db.session.commit()

    flash(
        "SOP uploaded successfully.",
        "success"
    )

    return redirect(
        url_for("head.dashboard")
    )


# =========================================================
# UPLOAD TRAINING MATERIAL
# =========================================================

@admin_bp.route(
    "/upload-training",
    methods=["POST"]
)
def upload_training():

    # -----------------------------------------------------
    # GET FILE
    # -----------------------------------------------------

    f = request.files.get("file")

    if not f or not f.filename:

        flash(
            "Choose a training file.",
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

    # -----------------------------------------------------
    # ALLOWED FILE TYPES
    # -----------------------------------------------------

    allowed_extensions = {
        ".pdf",
        ".mp4",
        ".webm",
        ".ogg",
        ".mov",
        ".avi",
        ".mkv"
    }

    extension = Path(
        filename
    ).suffix.lower()

    if extension not in allowed_extensions:

        flash(
            "Training files must be PDF or video files "
            "(PDF, MP4, WebM, OGG, MOV, AVI or MKV).",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    # -----------------------------------------------------
    # TRAINING INFORMATION
    # -----------------------------------------------------

    title = (
        request.form
        .get(
            "title",
            ""
        )
        .strip()
    )

    description = (
        request.form
        .get(
            "description",
            ""
        )
        .strip()
    )

    # -----------------------------------------------------
    # DEPARTMENT
    #
    # ADMIN / GM can select a department.
    # REGULAR HEAD automatically uses their department.
    # -----------------------------------------------------

    if current_user.role == "admin":

        training_department = (
            request.form
            .get(
                "department",
                ""
            )
            .strip()
        )

        if not training_department:

            training_department = current_user.department

    else:

        training_department = current_user.department

    # -----------------------------------------------------
    # TITLE IS REQUIRED
    # -----------------------------------------------------

    if not title:

        flash(
            "Training title is required.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    # -----------------------------------------------------
    # SAVE FILE
    # -----------------------------------------------------

    upload_folder = Path(
        current_app.config["UPLOAD_FOLDER"]
    )

    upload_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # Timestamp prevents files with the same name from
    # overwriting each other.

    saved_filename = (
        f"training_"
        f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_"
        f"{filename}"
    )

    path = (
        upload_folder
        / saved_filename
    )

    f.save(path)

    # -----------------------------------------------------
    # SAVE TRAINING RECORD
    # -----------------------------------------------------

    training = Training(
        title=title,
        department=training_department,
        description=description,
        filename=saved_filename,
        uploaded_by=current_user.name,
        uploaded_at=datetime.utcnow()
    )

    db.session.add(
        training
    )

    db.session.commit()

    flash(
        "Training material uploaded successfully.",
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

    audit_type = (
        request.form
        .get(
            "audit_type",
            ""
        )
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

    name = (
        request.form
        .get(
            "name",
            ""
        )
        .strip()
    )

    auditor = (
        request.form
        .get(
            "auditor",
            ""
        )
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
    # ADMIN / GM CAN SELECT A DEPARTMENT.
    # REGULAR HEAD USES THEIR OWN DEPARTMENT.
    # -----------------------------------------------------

    if current_user.role == "admin":

        audit_department = (
            request.form
            .get(
                "department",
                ""
            )
            .strip()
        )

        if not audit_department:

            audit_department = current_user.department

    else:

        audit_department = current_user.department

    audit = Audit(
        name=name,
        department=audit_department,
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
            "department": audit_department,
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
        .get(
            "name",
            ""
        )
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

    db.session.add(
        Holiday(
            name=name,
            date=d,
            holiday_type=request.form.get(
                "holiday_type",
                "Company"
            )
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

    if not employee:

        flash(
            "Employee could not be found.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    # -----------------------------------------------------
    # REGULAR HEAD
    # -----------------------------------------------------

    if (
        current_user.role == "head"
        and employee.department != current_user.department
    ):

        flash(
            "You can only raise an appraisal for an "
            "employee in your department.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    if employee.role != "employee":

        flash(
            "Appraisals can only be raised for employees.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    cycle = (
        request.form
        .get(
            "cycle",
            ""
        )
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

    db.session.add(
        Appraisal(
            employee_id=employee.employee_id,
            department=employee.department,
            cycle=cycle,
            stage="Raised",
            completion=10,
            next_date=next_date,
            raised_by=current_user.name
        )
    )

    db.session.commit()

    flash(
        "Appraisal raised.",
        "success"
    )

    return redirect(
        url_for("head.dashboard")
    )


# =========================================================
# COMPANY EVENTS (any department head or admin)
#
# Any department head (or the admin/General Manager) can
# create events and attach photos to them. The blueprint-
# level `protect()` above already restricts this whole
# section to role in ("head", "admin"), so no further role
# check is needed here. Employees can view events (see
# main.events) but not add to them.
# =========================================================

@admin_bp.route(
    "/events/add",
    methods=["POST"]
)
def add_event():

    title = (
        request.form
        .get("title", "")
        .strip()
    )

    try:

        event_date = datetime.strptime(
            request.form["event_date"],
            "%Y-%m-%d"
        ).date()

    except (ValueError, KeyError):

        flash(
            "Invalid event date.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    if not title:

        flash(
            "Event title is required.",
            "danger"
        )

        return redirect(
            url_for("head.dashboard")
        )

    db.session.add(
        Event(
            title=title,
            description=request.form.get(
                "description", ""
            ).strip(),
            event_date=event_date,
            created_by=current_user.name
        )
    )

    db.session.commit()

    flash(
        "Event added.",
        "success"
    )

    return redirect(
        url_for("head.dashboard")
    )


@admin_bp.route(
    "/events/<int:event_id>/photos",
    methods=["POST"]
)
def upload_event_photos(event_id):

    event = db.session.get(Event, event_id)

    if not event:
        abort(404)

    files = request.files.getlist("photos")

    upload_folder = Path(
        current_app.config["UPLOAD_FOLDER"]
    )

    upload_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    saved = 0

    for f in files:

        if not f or not f.filename:
            continue

        base_name = secure_filename(f.filename)

        if not base_name:
            continue

        # Prefixed with event id + timestamp so photos from
        # different events (or with generic camera filenames
        # like IMG_0001.jpg) never collide in the shared
        # uploads folder.
        filename = (
            f"event{event_id}_"
            f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_"
            f"{base_name}"
        )

        f.save(upload_folder / filename)

        db.session.add(
            EventPhoto(
                event_id=event_id,
                filename=filename,
                caption=request.form.get(
                    "caption", ""
                ).strip(),
                uploaded_by=current_user.name
            )
        )

        saved += 1

    db.session.commit()

    if saved:

        flash(
            f"{saved} photo(s) uploaded to \"{event.title}\".",
            "success"
        )

    else:

        flash(
            "No photos were uploaded.",
            "danger"
        )

    return redirect(
        url_for("head.dashboard")
    )
