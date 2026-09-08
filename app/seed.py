from . import db
from .models import User, Department


def seed():

    # =========================================================
    # DEPARTMENT HEAD ACCOUNTS
    # =========================================================
    #
    # Regular department heads keep normal "head" access.
    #
    # General Manager is handled separately below because
    # he needs access across ALL departments.
    #
    # =========================================================

    heads = [

        {
            "employee_id": "HEAD-HR",
            "name": "Mr. Chakrapani",
            "email": "chakrapani.rompicharla@bobbagroup.com",
            "password": "welcome123",
            "department": "HR",
            "designation": "HR",
        },

        {
            "employee_id": "HEAD-ADMIN",
            "name": "Mr. Vijay Kumar",
            "email": "vijaykumar@bobbagroup.com",
            "password": "welcome123",
            "department": "Admin",
            "designation": "Admin",
        },

        {
            "employee_id": "HEAD-OPERATION",
            "name": "Mr. Vijay Rozario",
            "email": "vijay.rozario@bobbagroup.com",
            "password": "welcome123",
            "department": "Operation",
            "designation": "Operation",
        },

        {
            "employee_id": "HEAD-FACILITY",
            "name": "Mr. Jayatheertha",
            "email": "jayatheertha.g@bobbagroup.com",
            "password": "welcome123",
            "department": "Facility",
            "designation": "Facility",
        },

        {
            "employee_id": "HEAD-IT",
            "name": "Mr. Bhanu Prakash",
            "email": "bl.itsupport@bobbagroup.com",
            "password": "welcome123",
            "department": "IT",
            "designation": "IT",
        },

        {
            "employee_id": "HEAD-SALES",
            "name": "Ms. Likhitha",
            "email": "likhitha.sheregar@bobbagroup.com",
            "password": "welcome123",
            "department": "Sales & Marketing",
            "designation": "Sales & Marketing",
        },

        {
            "employee_id": "HEAD-SECURITY",
            "name": "Mr. Midde Ganesh",
            "email": "midde.ganesh@bobbagroup.com",
            "password": "welcome123",
            "department": "Safety & Security",
            "designation": "Safety & Security",
        },

        {
            "employee_id": "HEAD-QUALITY",
            "name": "Mr. Praveen CN",
            "email": "praveen.cn@bobbagroup.com",
            "password": "welcome123",
            "department": "Quality Control",
            "designation": "Quality Control",
        },
    ]


    # =========================================================
    # CREATE / UPDATE REGULAR DEPARTMENT HEADS
    # =========================================================

    for data in heads:

        user = (
            User.query
            .filter_by(
                email=data["email"]
            )
            .first()
        )

        if not user:

            user = User(
                employee_id=data["employee_id"],
                name=data["name"],
                email=data["email"],
                password=data["password"],
                department=data["department"],
                designation=data["designation"],
                role="head",
                total_leave=16,
                paid_leave_limit=8,
                paid_leave_used=0,
                unpaid_leave_used=0
            )

            db.session.add(user)

        else:

            user.name = data["name"]
            user.department = data["department"]
            user.designation = data["designation"]
            user.role = "head"


    # =========================================================
    # GENERAL MANAGER
    # =========================================================
    #
    # GM receives full department-head/admin-level access.
    #
    # We use role="admin" so the GM is not restricted to
    # a single department.
    #
    # =========================================================

    gm = (
        User.query
        .filter_by(
            email="corpadmin@bobbagroup.com"
        )
        .first()
    )

    if not gm:

        gm = User(
            employee_id="GM-001",
            name="Mr. Seshagiri",
            email="corpadmin@bobbagroup.com",
            password="welcome123",
            department="General Management",
            designation="General Manager",
            role="admin",
            total_leave=16,
            paid_leave_limit=8,
            paid_leave_used=0,
            unpaid_leave_used=0
        )

        db.session.add(gm)

    else:

        gm.name = "Mr. Seshagiri"
        gm.department = "General Management"
        gm.designation = "General Manager"
        gm.role = "admin"


    # =========================================================
    # SYSTEM ADMINISTRATOR
    # =========================================================
    #
    # This account gets the SAME full access as the GM.
    #
    # =========================================================

    admin = (
        User.query
        .filter_by(
            email="admin@bobbagroup.com"
        )
        .first()
    )

    if not admin:

        admin = User(
            employee_id="ADMIN-001",
            name="System Administrator",
            email="admin@bobbagroup.com",
            password="welcome123",
            department="General Management",
            designation="System Administrator",
            role="admin",
            total_leave=16,
            paid_leave_limit=8,
            paid_leave_used=0,
            unpaid_leave_used=0
        )

        db.session.add(admin)

    else:

        admin.name = "System Administrator"
        admin.department = "General Management"
        admin.designation = "System Administrator"
        admin.role = "admin"


    # =========================================================
    # DEMO EMPLOYEE
    # =========================================================

    employee = (
        User.query
        .filter_by(
            email="employee@company.com"
        )
        .first()
    )

    if not employee:

        employee = User(
            employee_id="EMP-001",
            name="Demo Employee",
            email="employee@company.com",
            password="employee123",
            department="HR",
            designation="Employee",
            role="employee",
            total_leave=16,
            paid_leave_limit=8,
            paid_leave_used=0,
            unpaid_leave_used=0
        )

        db.session.add(employee)


    # =========================================================
    # REMOVE OLD MANJULA DIRECTORY RECORD
    # =========================================================

    old_manjula_records = (
        Department.query
        .filter(
            db.or_(
                Department.head_name.ilike("%manjula%"),
                Department.email.ilike(
                    "%manjula.gardampalli%"
                )
            )
        )
        .all()
    )

    for department in old_manjula_records:

        db.session.delete(department)


    # =========================================================
    # COMMIT
    # =========================================================

    db.session.commit()
