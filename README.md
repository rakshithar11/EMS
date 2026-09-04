
# Employee Management System — updated prototype

## Access model

### Employee
Employees can:
- Sign in
- Log attendance with Check-in / Check-out
- View attendance history
- Raise Paid or Unpaid holiday/leave requests
- View leave balance
- View holiday calendar
- View their appraisal status
- View SOPs, training and audit information
- View department heads and contact information
- Open common resources

There is **no Work From Home option**.

### Department Head
Only users with `role=head` can:
- Upload SOPs
- Add ISO/GDP audit dates
- Add holidays
- Approve/reject leave requests for their own department
- Raise appraisals for employees in their own department

## Leave policy

- Maximum total leave: **16 days**
- Maximum paid leave: **8 days**
- Remaining days are unpaid leave
- A request cannot exceed the employee's remaining total leave
- A Paid request cannot exceed the remaining paid leave
- No WFH leave/status exists in the application

## Editable master files

The `data/` folder contains the files that drive the informational sections.

Edit these files and refresh the website:

- `data/departments.csv`
- `data/common_urls.csv`
- `data/holidays.csv`
- `data/audits.csv`
- `data/training.csv`

The application re-reads these files before requests and updates the database when the file is valid.

### Important distinction

Attendance, leave requests, approvals and appraisals are **transactional records**, so they are created through the website rather than being overwritten by a master text file.

SOP documents are uploaded through the Department Head console.

This means the master-file approach is used for information that is naturally maintained as a list, while employee actions remain in the database.

## Supplied department-head contact sheet

Known heads from the supplied image have been entered only where the photo matches one of the requested departments:
- Admin — Mr. Vijay Kumar — Corporate Office
- HR — Mr. Chakrapani — Corporate Office
- Facilities — Mr. Jayatheertha — L1
- IT — Mr. Bhanu Prakash — L1
- Security — Mr. Midde Ganesh — L1

Accounts, Cold Storage (L2), and Dry Storage (L1) are intentionally marked **Not assigned** because their head details were not present in the supplied image.

The supplied image also contained General Manager, Operation, Customer Service, Sales & Marketing and Quality Control contacts; those were not assigned to the requested department list because doing so would require guessing the organizational mapping.

## Demo credentials

Employee:
- employee@company.com
- employee123

Department heads:
- HR: chakrapani.rompicharla@bobbagroup.com / welcome123
- Admin: vijaykumar@bobbagroup.com / welcome123
- Facilities: jayatheertha.g@bobbagroup.com / welcome123
- IT: bl.itsupport@bobbagroup.com / welcome123
- Security: midde.ganesh@bobbagroup.com / welcome123

Change demo passwords before any real use.

## Run

```text
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:5000`.

## Production hardening

This remains a prototype. Before real deployment:
- Hash passwords using Werkzeug/Argon2/bcrypt
- Use environment variables for secrets
- Use PostgreSQL/MySQL
- Add CSRF protection
- Add granular authorization
- Secure file storage and virus/type validation
- Add proper notifications/email
- Add database migrations
- Add real cloud file sync (Google Drive/OneDrive/SharePoint) if remote master files are required
