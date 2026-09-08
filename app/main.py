from datetime import date, datetime
from pathlib import Path

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_from_directory,
    abort,
    current_app
)

from flask_login import login_required, current_user

from . import db
from .models import (
    Attendance,
    Holiday,
    LeaveRequest,
    Appraisal,
    SOP,
    Training,
    Audit,
    Department,
    CommonURL,
    User
)


main_bp = Blueprint("main", __name__)


# =========================================================
# HOME
# =========================================================

@main_bp.route("/")
def index():

    return redirect(
        url_for("main.dashboard")
    )


# =========================================================
# EMPLOYEE DASHBOARD
# =========================================================

@main_bp.route("/dashboard")
@login_required
def dashboard():

    today = date.today()

    att = (
        Attendance.query
        .filter_by(
            employee_id=current_user.employee_id,
            date=today
        )
        .first()
    )

    attendance = (
        Attendance.query
        .filter_by(
            employee_id=current_user.employee_id
        )
        .order_by(
            Attendance.date.desc()
        )
        .limit(8)
        .all()
    )

    holidays = (
        Holiday.query
        .filter(
            Holiday.date >= today
        )
        .order_by(
            Holiday.date
        )
        .limit(5)
        .all()
    )

    requests = (
        LeaveRequest.query
        .filter_by(
            employee_id=current_user.employee_id
        )
        .order_by(
            LeaveRequest.created_at.desc()
        )
        .limit(5)
        .all()
    )

    appraisal = (
        Appraisal.query
        .filter_by(
            employee_id=current_user.employee_id
        )
        .order_by(
            Appraisal.id.desc()
        )
        .first()
    )

    paid_remaining = max(
        0,
        current_user.paid_leave_limit
        - current_user.paid_leave_used
    )

    total_used = (
        current_user.paid_leave_used
        + current_user.unpaid_leave_used
    )

    total_remaining = max(
        0,
        current_user.total_leave
        - total_used
    )

    return render_template(
        "dashboard.html",
        today_att=att,
        attendance=attendance,
        holidays=holidays,
        requests=requests,
        appraisal=appraisal,
        paid_remaining=paid_remaining,
        total_remaining=total_remaining
    )


# =========================================================
# ATTENDANCE
# =========================================================

@main_bp.route(
    "/attendance",
    methods=["GET", "POST"]
)
@login_required
def attendance():

    if current_user.role != "employee":

        return redirect(
            url_for("head.dashboard")
        )

    today = date.today()

    record = (
        Attendance.query
        .filter_by(
            employee_id=current_user.employee_id,
            date=today
        )
        .first()
    )

    if request.method == "POST":

        action = request.form["action"]

        # -------------------------------------------------
        # CHECK IN
        # -------------------------------------------------

        if action == "checkin":

            if record and record.check_in:

                flash(
                    "You have already logged your attendance today.",
                    "danger"
                )

            else:

                if not record:

                    record = Attendance(
                        employee_id=current_user.employee_id,
                        date=today
                    )

                    db.session.add(record)

                record.check_in = datetime.now()
                record.status = "Present"

                db.session.commit()

                flash(
                    "Check-in recorded.",
                    "success"
                )

        # -------------------------------------------------
        # CHECK OUT
        # -------------------------------------------------

        elif action == "checkout":

            if not record or not record.check_in:

                flash(
                    "Please check in first.",
                    "danger"
                )

            elif record.check_out:

                flash(
                    "You have already checked out today.",
                    "danger"
                )

            else:

                record.check_out = datetime.now()

                record.hours = round(
                    (
                        record.check_out
                        - record.check_in
                    ).total_seconds()
                    / 3600,
                    2
                )

                db.session.commit()

                flash(
                    "Check-out recorded.",
                    "success"
                )

        return redirect(
            url_for("main.attendance")
        )

    rows = (
        Attendance.query
        .filter_by(
            employee_id=current_user.employee_id
        )
        .order_by(
            Attendance.date.desc()
        )
        .all()
    )

    return render_template(
        "attendance.html",
        rows=rows,
        today_record=record
    )


# =========================================================
# LEAVE / HOLIDAY REQUEST
# =========================================================

@main_bp.route(
    "/leave",
    methods=["GET", "POST"]
)
@login_required
def leave():

    if current_user.role != "employee":

        return redirect(
            url_for("head.dashboard")
        )

    if request.method == "POST":

        # -------------------------------------------------
        # READ FORM
        # -------------------------------------------------

        try:

            start = datetime.strptime(
                request.form["start_date"],
                "%Y-%m-%d"
            ).date()

            end = datetime.strptime(
                request.form["end_date"],
                "%Y-%m-%d"
            ).date()

        except (ValueError, KeyError):

            flash(
                "Please enter valid leave dates.",
                "danger"
            )

            return redirect(
                url_for("main.leave")
            )

        days = (
            end - start
        ).days + 1

        leave_type = (
            request.form
            .get("leave_type", "")
            .strip()
        )

        selected_head_email = (
            request.form
            .get("forward_to", "")
            .strip()
        )

        # -------------------------------------------------
        # VALIDATE LEAVE TYPE
        # -------------------------------------------------

        if leave_type not in (
            "Paid",
            "Unpaid"
        ):

            flash(
                "Please select a valid leave type.",
                "danger"
            )

            return redirect(
                url_for("main.leave")
            )

        # -------------------------------------------------
        # FIND SELECTED DEPARTMENT HEAD
        #
        # Only users with role="head" can be selected.
        # -------------------------------------------------

        selected_head = (
            User.query
            .filter(
                User.role == "head",
                User.email == selected_head_email
            )
            .first()
        )

        if not selected_head:

            flash(
                "Please select a valid department head.",
                "danger"
            )

            return redirect(
                url_for("main.leave")
            )

        # -------------------------------------------------
        # LEAVE BALANCES
        # -------------------------------------------------

        paid_remaining = (
            current_user.paid_leave_limit
            - current_user.paid_leave_used
        )

        total_remaining = (
            current_user.total_leave
            - current_user.paid_leave_used
            - current_user.unpaid_leave_used
        )

        # -------------------------------------------------
        # VALIDATE DAYS
        # -------------------------------------------------

        if days <= 0:

            flash(
                "Invalid date range.",
                "danger"
            )

        elif days > total_remaining:

            flash(
                f"Only {total_remaining} total leave day(s) remain.",
                "danger"
            )

        elif (
            leave_type == "Paid"
            and days > paid_remaining
        ):

            flash(
                f"Only {paid_remaining} paid leave day(s) remain.",
                "danger"
            )

        else:

            # -------------------------------------------------
            # CHECK OVERLAPPING REQUESTS
            # -------------------------------------------------

            overlapping = (
                LeaveRequest.query
                .filter(
                    LeaveRequest.employee_id
                    == current_user.employee_id,

                    LeaveRequest.status.in_(
                        ["Pending", "Approved"]
                    ),

                    LeaveRequest.start_date <= end,

                    LeaveRequest.end_date >= start
                )
                .first()
            )

            if overlapping:

                flash(
                    "You already have a pending or approved "
                    "leave request for one or more of these dates.",
                    "danger"
                )

                return redirect(
                    url_for("main.leave")
                )

            # -------------------------------------------------
            # CREATE REQUEST
            # -------------------------------------------------

            leave_request = LeaveRequest(
                employee_id=current_user.employee_id,

                department=current_user.department,

                leave_type=leave_type,

                start_date=start,

                end_date=end,

                days=days,

                reason=request.form.get(
                    "reason",
                    ""
                ).strip(),

                status="Pending",

                forwarded_to=selected_head.email,

                forwarded_to_name=selected_head.name
            )

            db.session.add(
                leave_request
            )

            db.session.commit()

            flash(
                f"Holiday/leave request forwarded to "
                f"{selected_head.name}.",
                "success"
            )

        return redirect(
            url_for("main.leave")
        )

    # =====================================================
    # GET REQUEST
    # =====================================================

    requests = (
        LeaveRequest.query
        .filter_by(
            employee_id=current_user.employee_id
        )
        .order_by(
            LeaveRequest.created_at.desc()
        )
        .all()
    )

    paid_remaining = max(
        0,
        current_user.paid_leave_limit
        - current_user.paid_leave_used
    )

    total_remaining = max(
        0,
        current_user.total_leave
        - current_user.paid_leave_used
        - current_user.unpaid_leave_used
    )

    # -----------------------------------------------------
    # DEPARTMENT HEADS
    #
    # Only role="head" users appear in the selector.
    #
    # Mrs. Manjula cannot appear because she is not a
    # department head.
    # -----------------------------------------------------

    department_heads = (
        User.query
        .filter(
            User.role == "head"
        )
        .order_by(
            User.name
        )
        .all()
    )

    return render_template(
        "leave.html",
        requests=requests,
        paid_remaining=paid_remaining,
        total_remaining=total_remaining,
        department_heads=department_heads
    )


# =========================================================
# APPRAISAL
# =========================================================

@main_bp.route("/appraisal")
@login_required
def appraisal():

    rows = (
        Appraisal.query
        .filter_by(
            employee_id=current_user.employee_id
        )
        .all()
    )

    return render_template(
        "appraisal.html",
        rows=rows
    )


# =========================================================
# KNOWLEDGE & COMPLIANCE
# =========================================================

@main_bp.route("/knowledge")
@login_required
def knowledge():

    return render_template(
        "knowledge.html",

        sops=(
            SOP.query
            .order_by(
                SOP.uploaded_at.desc()
            )
            .all()
        ),

        training=(
            Training.query
            .order_by(
                Training.title
            )
            .all()
        ),

        audits=(
            Audit.query
            .order_by(
                Audit.audit_date
            )
            .all()
        )
    )


# =========================================================
# OPEN SOP
# =========================================================

@main_bp.route(
    "/sop/<int:sop_id>"
)
@login_required
def open_sop(sop_id):

    sop = db.session.get(
        SOP,
        sop_id
    )

    if not sop or not sop.filename:

        abort(404)

    file_path = (
        Path(
            current_app.config["UPLOAD_FOLDER"]
        )
        / sop.filename
    )

    if not file_path.exists():

        abort(404)

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        sop.filename,
        as_attachment=False
    )


# =========================================================
# INTERDEPARTMENTAL DIRECTORY
# =========================================================

@main_bp.route(
    "/departments"
)
@login_required
def departments():

    q = (
        request.args
        .get(
            "q",
            ""
        )
        .strip()
    )

    query = Department.query

    if q:

        query = query.filter(
            (
                Department.name
                .ilike(f"%{q}%")
            )
            |
            (
                Department.head_name
                .ilike(f"%{q}%")
            )
        )

    departments = (
        query
        .order_by(
            Department.name
        )
        .all()
    )

    # -----------------------------------------------------
    # REMOVE OLD MANJULA RECORD
    #
    # Manjula is no longer in departments.csv, but an old
    # database record may still exist. This prevents her
    # from being displayed while the database is refreshed.
    # -----------------------------------------------------

    departments = [
        department
        for department in departments
        if (
            not department.head_name
            or "manjula" not in
            department.head_name.lower()
        )
    ]

    return render_template(
        "departments.html",
        departments=departments,
        q=q
    )


# =========================================================
# COMMON RESOURCES / URLS
# =========================================================

@main_bp.route(
    "/resources"
)
@login_required
def resources():

    q = (
        request.args
        .get(
            "q",
            ""
        )
        .strip()
    )

    query = CommonURL.query

    if q:

        query = query.filter(
            (
                CommonURL.name
                .ilike(f"%{q}%")
            )
            |
            (
                CommonURL.category
                .ilike(f"%{q}%")
            )
        )

    return render_template(
        "resources.html",
        resources=(
            query
            .order_by(
                CommonURL.name
            )
            .all()
        ),
        q=q
    )
