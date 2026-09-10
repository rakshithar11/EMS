"""
Tiny auto-migration for SQLite.

This project has no migration framework (no Flask-Migrate/Alembic).
db.create_all() only creates tables that don't exist yet — it will
NOT add new columns to a table that's already there. This helper
adds any columns a model defines but the existing table is missing,
so an existing ems.db keeps its data when the schema grows.
"""
import sqlalchemy as sa


# Map of table -> {column: DDL type/default} for columns that may be
# missing from a database created before that column was added.
_NEW_COLUMNS = {
    "leave_request": {
        "holiday_days": "INTEGER DEFAULT 0",
        "chargeable_days": "INTEGER",
        "approved_paid_days": "INTEGER DEFAULT 0",
        "approved_unpaid_days": "INTEGER DEFAULT 0",
    },
}


def run_auto_migrations(engine):
    inspector = sa.inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.connect() as conn:
        for table, columns in _NEW_COLUMNS.items():
            if table not in existing_tables:
                continue  # db.create_all() will make it with all columns

            existing_columns = {
                col["name"] for col in inspector.get_columns(table)
            }

            for name, ddl in columns.items():
                if name in existing_columns:
                    continue
                conn.execute(
                    sa.text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                )

        conn.commit()

        # Backfill: any leave request created before this column
        # existed had no holiday overlap calculated, so treat every
        # requested day as chargeable (unchanged behaviour for it).
        if "leave_request" in existing_tables:
            conn.execute(
                sa.text(
                    "UPDATE leave_request SET chargeable_days = days "
                    "WHERE chargeable_days IS NULL"
                )
            )
            conn.commit()
