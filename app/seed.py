
from . import db
from .models import User, Attendance, Appraisal
from datetime import datetime

HEADS = [
    # Name, department, designation, email, phone, office
    ("Mr. Chakrapani", "HR", "Head - HR", "chakrapani.rompicharla@bobbagroup.com", "9448179993", "Corporate Office"),
    ("Mr. Vijay Kumar", "Admin", "Head - Admin", "vijaykumar@bobbagroup.com", "9980998584", "Corporate Office"),
    ("Mr. Jayatheertha", "Facilities", "Head - Facilities", "jayatheertha.g@bobbagroup.com", "9606003071", "L1"),
    ("Mr. Bhanu Prakash", "IT", "Head - IT", "bl.itsupport@bobbagroup.com", "9606003072", "L1"),
    ("Mr. Midde Ganesh", "Security", "Head - Security", "midde.ganesh@bobbagroup.com", "9606003073", "L1"),
]

def seed():
    if not User.query.first():
        db.session.add(User(employee_id="EMP001", name="Demo Employee",
                            email="employee@company.com", password="employee123",
                            department="HR", designation="Employee", role="employee"))
        for i, (name, dept, designation, email, phone, office) in enumerate(HEADS, start=10):
            db.session.add(User(employee_id=f"HEAD{i}", name=name, email=email,
                                password="welcome123", department=dept,
                                designation=designation, role="head"))
        db.session.commit()

    if not Attendance.query.first():
        # Start with no fake attendance; employees create their own records.
        pass

    if not Appraisal.query.first():
        pass

    # Ensure all requested departments exist in the editable master file.
    # Accounts, Cold Storage and Dry Storage intentionally have no head assigned
    # because the supplied contact sheet did not provide those names.
