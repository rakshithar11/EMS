from pathlib import Path
import csv

from . import db
from .models import (
    CommonURL,
    Department,
    Holiday,
    Audit,
    Training,
    SyncLog
)


def _read_csv(path):
    """
    Read a CSV file and return its rows as dictionaries.
    Returns an empty list if the file does not exist.
    """

    if not path.exists():
        return []

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        return list(
            csv.DictReader(f)
        )


def sync_from_csv(app):
    """
    Synchronize static CSV data with the database.

    Audits are treated carefully because department heads
    can add audits directly through the application.
    Those audits are already written back to audits.csv
    by admin.py.
    """

    data_folder = Path(
        app.config["DATA_FOLDER"]
    )

    try:

        # =================================================
        # COMMON URLS
        # =================================================

        common_urls_file = (
            data_folder / "common_urls.csv"
        )

        rows = _read_csv(
            common_urls_file
        )

        CommonURL.query.delete()

        for row in rows:

            if not row.get("name") or not row.get("url"):
                continue

            db.session.add(
                CommonURL(
                    name=row.get("name", "").strip(),
                    description=row.get(
                        "description",
                        ""
                    ).strip(),
                    category=row.get(
                        "category",
                        ""
                    ).strip(),
                    department=row.get(
                        "department",
                        ""
                    ).strip(),
                    url=row.get(
                        "url",
                        ""
                    ).strip()
                )
            )


        # =================================================
        # DEPARTMENTS
        # =================================================

        departments_file = (
            data_folder / "departments.csv"
        )

        rows = _read_csv(
            departments_file
        )

        Department.query.delete()

        for row in rows:

            if not row.get("name"):
                continue

            db.session.add(
                Department(
                    name=row.get(
                        "name",
                        ""
                    ).strip(),

                    head_name=row.get(
                        "head_name",
                        ""
                    ).strip(),

                    designation=row.get(
                        "designation",
                        ""
                    ).strip(),

                    email=row.get(
                        "email",
                        ""
                    ).strip(),

                    phone=row.get(
                        "phone",
                        ""
                    ).strip(),

                    extension=row.get(
                        "extension",
                        ""
                    ).strip(),

                    office=row.get(
                        "office",
                        ""
                    ).strip(),

                    floor=row.get(
                        "floor",
                        ""
                    ).strip(),

                    room=row.get(
                        "room",
                        ""
                    ).strip(),

                    description=row.get(
                        "description",
                        ""
                    ).strip()
                )
            )


        # =================================================
        # HOLIDAYS
        # =================================================

        holidays_file = (
            data_folder / "holidays.csv"
        )

        rows = _read_csv(
            holidays_file
        )

        Holiday.query.delete()

        for row in rows:

            if not row.get("name") or not row.get("date"):
                continue

            from datetime import datetime

            try:

                holiday_date = datetime.strptime(
                    row["date"].strip(),
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                continue

            db.session.add(
                Holiday(
                    name=row.get(
                        "name",
                        ""
                    ).strip(),

                    date=holiday_date,

                    holiday_type=row.get(
                        "holiday_type",
                        "Company"
                    ).strip()
                )
            )


        # =================================================
        # AUDITS
        # =================================================
        #
        # IMPORTANT:
        # admin.py now writes newly created audits into
        # audits.csv.
        #
        # Therefore it is safe for sync to rebuild the
        # Audit table from the CSV.
        #
        # =================================================

        audits_file = (
            data_folder / "audits.csv"
        )

        rows = _read_csv(
            audits_file
        )

        Audit.query.delete()

        from datetime import datetime

        for row in rows:

            if (
                not row.get("name")
                or not row.get("audit_date")
            ):
                continue

            try:

                audit_date = datetime.strptime(
                    row["audit_date"].strip(),
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                continue

            next_audit_date = None

            if row.get("next_audit_date"):

                try:

                    next_audit_date = datetime.strptime(
                        row["next_audit_date"].strip(),
                        "%Y-%m-%d"
                    ).date()

                except ValueError:

                    next_audit_date = None

            db.session.add(
                Audit(
                    name=row.get(
                        "name",
                        ""
                    ).strip(),

                    department=row.get(
                        "department",
                        ""
                    ).strip(),

                    audit_type=row.get(
                        "audit_type",
                        ""
                    ).strip(),

                    auditor=row.get(
                        "auditor",
                        ""
                    ).strip(),

                    audit_date=audit_date,

                    next_audit_date=next_audit_date,

                    status=row.get(
                        "status",
                        "Upcoming"
                    ).strip()
                )
            )


        # =================================================
        # TRAINING
        # =================================================

        training_file = (
            data_folder / "training.csv"
        )

        rows = _read_csv(
            training_file
        )

        Training.query.delete()

        for row in rows:

            if not row.get("title"):
                continue

            mandatory_value = (
                row.get(
                    "mandatory",
                    ""
                )
                .strip()
                .lower()
            )

            mandatory = mandatory_value in (
                "yes",
                "true",
                "1",
                "mandatory"
            )

            db.session.add(
                Training(
                    title=row.get(
                        "title",
                        ""
                    ).strip(),

                    description=row.get(
                        "description",
                        ""
                    ).strip(),

                    department=row.get(
                        "department",
                        ""
                    ).strip(),

                    duration=row.get(
                        "duration",
                        ""
                    ).strip(),

                    mandatory=mandatory,

                    url=row.get(
                        "url",
                        ""
                    ).strip()
                )
            )


        # =================================================
        # SAVE
        # =================================================

        db.session.commit()

        db.session.add(
            SyncLog(
                source="CSV",
                status="Success",
                message="CSV data synchronized successfully."
            )
        )

        db.session.commit()


    except Exception as e:

        db.session.rollback()

        db.session.add(
            SyncLog(
                source="CSV",
                status="Failed",
                message=str(e)
            )
        )

        db.session.commit()

        raise
