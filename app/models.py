from datetime import datetime

from flask_login import UserMixin

from . import db


# =========================================================
# USER
# =========================================================

class User(UserMixin, db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    employee_id = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    department = db.Column(
        db.String(100)
    )

    designation = db.Column(
        db.String(100)
    )

    # employee | head | admin
    role = db.Column(
        db.String(30),
        default="employee"
    )

    total_leave = db.Column(
        db.Integer,
        default=16
    )

    paid_leave_limit = db.Column(
        db.Integer,
        default=8
    )

    paid_leave_used = db.Column(
        db.Integer,
        default=0
    )

    unpaid_leave_used = db.Column(
        db.Integer,
        default=0
    )


# =========================================================
# ATTENDANCE
# =========================================================

class Attendance(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    employee_id = db.Column(
        db.String(50),
        nullable=False
    )

    date = db.Column(
        db.Date,
        nullable=False
    )

    check_in = db.Column(
        db.DateTime
    )

    check_out = db.Column(
        db.DateTime
    )

    status = db.Column(
        db.String(30),
        default="Present"
    )

    hours = db.Column(
        db.Float,
        default=0
    )


# =========================================================
# HOLIDAY
# =========================================================

class Holiday(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    date = db.Column(
        db.Date,
        nullable=False
    )

    holiday_type = db.Column(
        db.String(50),
        default="Company"
    )


# =========================================================
# LEAVE REQUEST
# =========================================================

class LeaveRequest(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    employee_id = db.Column(
        db.String(50),
        nullable=False
    )

    department = db.Column(
        db.String(100)
    )

    leave_type = db.Column(
        db.String(30),
        nullable=False
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    end_date = db.Column(
        db.Date,
        nullable=False
    )

    days = db.Column(
        db.Integer,
        nullable=False
    )

    reason = db.Column(
        db.Text
    )

    status = db.Column(
        db.String(30),
        default="Pending"
    )

    # -----------------------------------------------------
    # NEW
    # Company holidays that fall inside [start_date, end_date]
    # don't consume leave balance. `days` stays the full
    # calendar span (for display); `chargeable_days` is what
    # actually gets deducted on approval.
    # -----------------------------------------------------

    holiday_days = db.Column(
        db.Integer,
        default=0
    )

    chargeable_days = db.Column(
        db.Integer
    )

    # -----------------------------------------------------
    # NEW
    # The head approving the request can split the chargeable
    # days between paid and unpaid instead of it being forced
    # to match the employee's originally requested leave_type.
    # -----------------------------------------------------

    approved_paid_days = db.Column(
        db.Integer,
        default=0
    )

    approved_unpaid_days = db.Column(
        db.Integer,
        default=0
    )

    head_comment = db.Column(
        db.Text
    )

    # -----------------------------------------------------
    # NEW
    # The department head selected by the employee.
    # This stores the email address so the request can be
    # routed to the correct head.
    # -----------------------------------------------------

    forwarded_to = db.Column(
        db.String(150)
    )

    forwarded_to_name = db.Column(
        db.String(120)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# APPRAISAL
# =========================================================

class Appraisal(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    employee_id = db.Column(
        db.String(50),
        nullable=False
    )

    department = db.Column(
        db.String(100)
    )

    cycle = db.Column(
        db.String(100),
        nullable=False
    )

    stage = db.Column(
        db.String(50),
        default="Raised"
    )

    completion = db.Column(
        db.Integer,
        default=10
    )

    next_date = db.Column(
        db.Date
    )

    raised_by = db.Column(
        db.String(120)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# SOP
# =========================================================

class SOP(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(200),
        nullable=False
    )

    code = db.Column(
        db.String(80)
    )

    department = db.Column(
        db.String(100)
    )

    version = db.Column(
        db.String(30),
        default="1.0"
    )

    filename = db.Column(
        db.String(255)
    )

    uploaded_by = db.Column(
        db.String(120)
    )

    uploaded_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    review_date = db.Column(
        db.Date
    )


# =========================================================
# TRAINING
# =========================================================

class Training(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    department = db.Column(
        db.String(100)
    )

    duration = db.Column(
        db.String(30)
    )

    mandatory = db.Column(
        db.Boolean,
        default=False
    )

    # Existing external URL support
    url = db.Column(
        db.String(500)
    )

    # -----------------------------------------------------
    # NEW
    # Uploaded training file.
    # Can contain PDF/video filename.
    # -----------------------------------------------------

    filename = db.Column(
        db.String(255)
    )

    uploaded_by = db.Column(
        db.String(120)
    )

    uploaded_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# AUDIT
# =========================================================

class Audit(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(200),
        nullable=False
    )

    department = db.Column(
        db.String(100)
    )

    audit_type = db.Column(
        db.String(80)
    )

    auditor = db.Column(
        db.String(120)
    )

    audit_date = db.Column(
        db.Date
    )

    next_audit_date = db.Column(
        db.Date
    )

    status = db.Column(
        db.String(30),
        default="Upcoming"
    )

    findings = db.Column(
        db.Text
    )

    corrective_action = db.Column(
        db.Text
    )

    responsible_person = db.Column(
        db.String(120)
    )

    due_date = db.Column(
        db.Date
    )


# =========================================================
# DEPARTMENT
# =========================================================

class Department(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    head_name = db.Column(
        db.String(120)
    )

    designation = db.Column(
        db.String(120)
    )

    email = db.Column(
        db.String(150)
    )

    phone = db.Column(
        db.String(50)
    )

    extension = db.Column(
        db.String(30)
    )

    office = db.Column(
        db.String(100)
    )

    floor = db.Column(
        db.String(30)
    )

    room = db.Column(
        db.String(50)
    )

    description = db.Column(
        db.Text
    )


# =========================================================
# COMMON URL
# =========================================================

class CommonURL(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    category = db.Column(
        db.String(80)
    )

    department = db.Column(
        db.String(100)
    )

    url = db.Column(
        db.String(500),
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# =========================================================
# COMPANY EVENT
# =========================================================
#
# Added by the admin (General Manager) only. Employees and
# heads can view events and their photos, but only the admin
# can create an event or attach photos to it afterwards.

class Event(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    event_date = db.Column(
        db.Date,
        nullable=False
    )

    created_by = db.Column(
        db.String(120)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    photos = db.relationship(
        "EventPhoto",
        backref="event",
        cascade="all, delete-orphan",
        order_by="EventPhoto.uploaded_at"
    )


# =========================================================
# EVENT PHOTO
# =========================================================

class EventPhoto(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("event.id"),
        nullable=False
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    caption = db.Column(
        db.String(200)
    )

    uploaded_by = db.Column(
        db.String(120)
    )

    uploaded_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================================
# SYNC LOG
# =========================================================

class SyncLog(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    source = db.Column(
        db.String(100),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False
    )

    message = db.Column(
        db.Text
    )

    synced_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
