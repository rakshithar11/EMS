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
    User,
    Event,
    EventPhoto
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

    # =====================================================
    # EVERY LOGGED-IN USER CAN LOG THEIR OWN ATTENDANCE
    # =====================================================

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

        action = request.form.get("action", "").strip()

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

        else:

            flash(
                "Invalid attendance action.",
                "danger"
            )

        return redirect(
            url_for("main.attendance")
        )


    # =====================================================
    # ATTENDANCE VIEW PERMISSIONS
    # =====================================================
    #
    # Employee:
    #     Own attendance only
    #
    # Department Head:
    #     Own attendance + employees in own department
    #
    # Admin / GM:
    #     All employees
    #
    # =====================================================

    can_view_all_attendance = (
        current_user.role == "admin"
    )

    if can_view_all_attendance:

        rows = (
            Attendance.query
            .order_by(
                Attendance.date.desc(),
                Attendance.employee_id
            )
            .all()
        )

        attendance_users = (
            User.query
            .order_by(
                User.name
            )
            .all()
        )

    elif current_user.role == "head":

        department_employees = (
            User.query
            .filter_by(
                department=current_user.department
            )
            .all()
        )

        employee_ids = [
            user.employee_id
            for user in department_employees
        ]

        # Always include the head's own attendance.
        if current_user.employee_id not in employee_ids:
            employee_ids.append(
                current_user.employee_id
            )

        rows = (
            Attendance.query
            .filter(
                Attendance.employee_id.in_(employee_ids)
            )
            .order_by(
                Attendance.date.desc(),
                Attendance.employee_id
            )
            .all()
        )

        attendance_users = department_employees

        if current_user.employee_id not in [
            user.employee_id
            for user in attendance_users
        ]:
            attendance_users.append(current_user)

    else:

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

        attendance_users = [current_user]


    return render_template(
        "attendance.html",
        rows=rows,
        today_record=record,
        attendance_users=attendance_users,
        can_view_all_attendance=(
            can_view_all_attendance
            or current_user.role == "head"
        )
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


        # ---------------------------------------------------
        # NEW
        # Company holidays inside [start, end] don't consume
        # leave balance. Only the remaining days are
        # "chargeable" against paid/unpaid balance.
        # ---------------------------------------------------

        holiday_days = (
            Holiday.query
            .filter(
                Holiday.date >= start,
                Holiday.date <= end
            )
            .count()
        )

        chargeable_days = max(
            0,
            days - holiday_days
        )


        leave_type = (
            request.form
            .get(
                "leave_type",
                ""
            )
            .strip()
        )


        selected_head_email = (
            request.form
            .get(
                "forward_to",
                ""
            )
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
        #
        # Validation runs against chargeable_days (calendar
        # days minus any company holidays in range), not the
        # raw calendar span, since holiday days need no leave
        # balance at all.
        # -------------------------------------------------

        if days <= 0:

            flash(
                "Invalid date range.",
                "danger"
            )

        elif chargeable_days > total_remaining:

            flash(
                f"Only {total_remaining} total leave day(s) remain. "
                f"This request needs {chargeable_days} chargeable "
                f"day(s) ({holiday_days} of the {days} calendar "
                f"day(s) already fall on a company holiday).",
                "danger"
            )

        elif (
            leave_type == "Paid"
            and chargeable_days > paid_remaining
        ):

            flash(
                f"Only {paid_remaining} paid leave day(s) remain, "
                f"but this request needs {chargeable_days} paid "
                f"day(s) after excluding {holiday_days} holiday day(s).",
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

                holiday_days=holiday_days,

                chargeable_days=chargeable_days,

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

            holiday_note = (
                f" ({holiday_days} of {days} day(s) fall on a "
                f"company holiday and won't be charged)"
                if holiday_days
                else ""
            )

            flash(
                f"Holiday/leave request forwarded to "
                f"{selected_head.name}{holiday_note}.",
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


    # -----------------------------------------------------
    # Holiday dates, for the live "chargeable days" preview
    # on the request form. The server still recalculates and
    # enforces this on submit — this is just a UI convenience.
    # -----------------------------------------------------

    holiday_dates = [
        holiday.date.isoformat()
        for holiday in Holiday.query.all()
    ]

    return render_template(
        "leave.html",
        requests=requests,
        paid_remaining=paid_remaining,
        total_remaining=total_remaining,
        department_heads=department_heads,
        holiday_dates=holiday_dates
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

        trainings=(
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
# OPEN TRAINING MATERIAL
# =========================================================

@main_bp.route(
    "/training/<int:training_id>"
)
@login_required
def open_training(training_id):

    training = db.session.get(
        Training,
        training_id
    )

    if not training or not training.filename:

        abort(404)


    file_path = (
        Path(
            current_app.config["UPLOAD_FOLDER"]
        )
        / training.filename
    )


    if not file_path.exists():

        abort(404)


    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        training.filename,
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


# =========================================================
# COMPANY EVENTS (view — everyone)
#
# Adding events / uploading photos is admin-only, handled in
# head.py (see head.add_event / head.upload_event_photos).
# This page just lists them for everyone to browse.
# =========================================================

@main_bp.route(
    "/events"
)
@login_required
def events():

    all_events = (
        Event.query
        .order_by(
            Event.event_date.desc()
        )
        .all()
    )

    return render_template(
        "events.html",
        events=all_events,
        today=date.today()
    )


@main_bp.route(
    "/events/photo/<int:photo_id>"
)
@login_required
def event_photo(photo_id):

    photo = db.session.get(
        EventPhoto,
        photo_id
    )

    if not photo:
        abort(404)

    file_path = (
        Path(
            current_app.config["UPLOAD_FOLDER"]
        )
        / photo.filename
    )

    if not file_path.exists():
        abort(404)

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        photo.filename,
        as_attachment=False
    )


# =========================================================
# ABOUT THE COMPANY
# =========================================================

@main_bp.route(
    "/about"
)
@login_required
def about():

    return render_template(
        "about.html"
    )
