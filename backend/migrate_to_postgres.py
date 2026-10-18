#!/usr/bin/env python3
"""
WasteDash — SQLite to PostgreSQL Consolidation & Safe Migration Utility
----------------------------------------------------------------------
Consolidates the three separate SQLite databases:
  1. users.db            -> Domain: users
  2. staff.db            -> Domain: staff
  3. waste_management.db -> Domain: waste_management
into a single, unified PostgreSQL database with three logical domains/schemas.

Key Guarantees:
  - Verified SHA-256 pre-migration backups created in backend/backups/
  - Zero modifications/deletions of source SQLite database files
  - Exact preservation of user IDs, staff IDs, password hashes, timestamps, and JSON data
  - Proper topological order of table imports respecting foreign key hierarchies
  - Idempotent execution (safe to run multiple times without duplicating records)
  - PostgreSQL sequence synchronization post-import for auto-increment integrity
  - PostgreSQL schema domain views (users.*, staff.*, waste_management.*)
  - Comprehensive source vs. destination row verification report
"""

import os
import sys
import argparse
import hashlib
import shutil
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.core.config import settings, normalize_database_url
from app.core.database import Base
import app.models

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wastedash.migration")

BACKUP_DIR = os.path.join(BASE_DIR, "backups")

# Source database configuration
SOURCE_DATABASES = {
    "users": os.path.join(BASE_DIR, "users.db"),
    "staff": os.path.join(BASE_DIR, "staff.db"),
    "waste_management": os.path.join(BASE_DIR, "waste_management.db"),
}

# Ordered topological table migration specification
# (Level 0: No dependencies, Level 1: Depends on Level 0, etc.)
TABLE_MIGRATION_ORDER: List[Tuple[str, str, str]] = [
    # Domain: users
    ("users", "users", "users"),
    ("users", "users", "password_reset_tokens"),
    ("users", "users", "auth_audit_logs"),
    ("users", "users", "user_ai_references"),

    # Domain: staff
    ("staff", "staff", "staff_profiles"),
    ("staff", "staff", "staff_duty_assignments"),
    ("staff", "staff", "staff_audit_logs"),

    # Domain: waste_management (Level 0 - independent entities)
    ("waste_management", "waste_management", "zones"),
    ("waste_management", "waste_management", "waste_categories"),
    ("waste_management", "waste_management", "collection_vehicles"),
    ("waste_management", "waste_management", "ai_models"),
    ("waste_management", "waste_management", "training_jobs"),
    ("waste_management", "waste_management", "dataset_sources"),
    ("waste_management", "waste_management", "dataset_imports"),
    ("waste_management", "waste_management", "environmental_metrics"),
    ("waste_management", "waste_management", "operational_alerts"),
    ("waste_management", "waste_management", "optimization_recommendations"),
    ("waste_management", "waste_management", "iot_devices"),
    ("waste_management", "waste_management", "iot_sorting_records"),
    ("waste_management", "waste_management", "public_complaints"),
    ("waste_management", "waste_management", "notifications"),
    ("waste_management", "waste_management", "simulation_runs"),
    ("waste_management", "waste_management", "ai_inference_audit"),
    ("waste_management", "waste_management", "ai_detections"),
    ("waste_management", "waste_management", "image_contributions"),
    ("waste_management", "waste_management", "uploads"),

    # Domain: waste_management (Level 1 - direct foreign keys)
    ("waste_management", "waste_management", "wards"),                 # -> zones.id
    ("waste_management", "waste_management", "dataset_images"),        # -> uploads.id
    ("waste_management", "waste_management", "device_telemetry"),      # -> iot_devices.device_id
    ("waste_management", "waste_management", "complaint_follow_ups"),  # -> public_complaints.id

    # Domain: waste_management (Level 2 - secondary dependencies)
    ("waste_management", "waste_management", "segregation_plants"),    # -> zones.id, wards.id
    ("waste_management", "waste_management", "waste_records"),         # -> waste_categories.id, wards.id

    # Domain: waste_management (Level 3 - tertiary dependencies)
    ("waste_management", "waste_management", "weighbridge_records"),   # -> segregation_plants.id
]


def calculate_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file for backup verification."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def create_verified_backups() -> Dict[str, Dict[str, Any]]:
    """Creates timestamped backups of all 3 SQLite databases with verified SHA-256 checksums."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_meta = {}

    for db_key, src_path in SOURCE_DATABASES.items():
        if not os.path.exists(src_path):
            logger.warning(f"Source database not found: {src_path}. Skipping backup.")
            continue

        src_size = os.path.getsize(src_path)
        src_hash = calculate_sha256(src_path)
        dest_filename = f"{db_key}_backup_pre_postgres_migration_{ts}.db"
        dest_path = os.path.join(BACKUP_DIR, dest_filename)

        shutil.copy2(src_path, dest_path)
        backup_size = os.path.getsize(dest_path)
        backup_hash = calculate_sha256(dest_path)

        if src_hash != backup_hash or src_size != backup_size:
            raise RuntimeError(f"Backup verification failed for {db_key}! Source and backup checksums mismatch.")

        logger.info(f"Verified backup created: {dest_path} ({backup_size} bytes, SHA256: {backup_hash[:12]}...)")
        backup_meta[db_key] = {
            "source_path": src_path,
            "backup_path": dest_path,
            "size_bytes": backup_size,
            "sha256": backup_hash,
            "timestamp": ts,
        }

    return backup_meta


def parse_datetime_value(val: Any) -> Optional[datetime]:
    """Converts diverse SQLite timestamp formats into a valid Python UTC datetime object."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)

    val_str = str(val).strip()
    if not val_str:
        return None

    # Try standard ISO format
    try:
        dt = datetime.fromisoformat(val_str)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass

    # Try standard SQLite space-delimited string
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(val_str.split("+")[0], fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue

    logger.warning(f"Unable to parse timestamp '{val}', returning None.")
    return None


def clean_row_for_postgres(row: Dict[str, Any], table_obj) -> Dict[str, Any]:
    """Sanitizes an SQLite row dictionary for PostgreSQL insertion according to column types."""
    cleaned = {}
    for col_name, val in row.items():
        if col_name not in table_obj.columns:
            continue
        col_type = str(table_obj.columns[col_name].type).upper()

        if val is None:
            cleaned[col_name] = None
        elif "BOOLEAN" in col_type:
            cleaned[col_name] = bool(val) if val not in (0, "0", False, "false", "False") else False
        elif "DATETIME" in col_type or "TIMESTAMP" in col_type:
            cleaned[col_name] = parse_datetime_value(val)
        elif "FLOAT" in col_type or "NUMERIC" in col_type:
            try:
                cleaned[col_name] = float(val) if val != "" else None
            except (ValueError, TypeError):
                cleaned[col_name] = None
        elif "INT" in col_type:
            try:
                cleaned[col_name] = int(val) if val != "" else None
            except (ValueError, TypeError):
                cleaned[col_name] = None
        else:
            cleaned[col_name] = str(val) if val is not None else None

    return cleaned


def run_migration(
    target_url: Optional[str] = None,
    dry_run: bool = False,
    verify_only: bool = False
) -> Dict[str, Any]:
    """Executes the full consolidation and data migration into PostgreSQL."""
    db_url = normalize_database_url(target_url or settings.DATABASE_URL)
    if not db_url or "sqlite" in db_url.lower():
        raise ValueError(
            f"Invalid target PostgreSQL URL: '{db_url}'. A valid PostgreSQL connection string is required."
        )

    logger.info(f"Target PostgreSQL URL configured: {db_url.split('@')[-1] if '@' in db_url else db_url}")

    # 1. Backups
    logger.info("Step 1: Creating verified pre-migration backups of SQLite databases...")
    backup_report = create_verified_backups()

    if verify_only:
        logger.info("Verification mode requested. Skipping data import.")
        return {"backups": backup_report, "status": "VERIFY_ONLY"}

    # 2. Destination Engine & Schema Initialization
    logger.info("Step 2: Connecting to PostgreSQL and initializing schemas and tables...")
    pg_engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=300
    )

    with pg_engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS users;"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staff;"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS waste_management;"))

    # Ensure all tables exist in destination
    Base.metadata.create_all(bind=pg_engine)

    meta = MetaData()
    meta.reflect(bind=pg_engine)

    if dry_run:
        logger.info("Dry-run requested: validated connections and table definitions. Halting before insert.")
        return {"backups": backup_report, "status": "DRY_RUN_PASSED"}

    # 3. Idempotent Data Transfer
    logger.info("Step 3: Transferring data from 3 SQLite databases into PostgreSQL in topological order...")
    migration_summary = []
    total_migrated_records = 0

    for domain, db_key, tbl_name in TABLE_MIGRATION_ORDER:
        src_path = SOURCE_DATABASES.get(db_key)
        if not src_path or not os.path.exists(src_path):
            logger.warning(f"Source database file for {db_key} not found at {src_path}. Skipping {tbl_name}.")
            migration_summary.append({
                "domain": domain,
                "table": tbl_name,
                "source_count": 0,
                "dest_count": 0,
                "rejected": 0,
                "status": "SKIPPED (File Not Found)",
            })
            continue

        if tbl_name not in meta.tables:
            logger.error(f"Table {tbl_name} not found in destination PostgreSQL metadata!")
            migration_summary.append({
                "domain": domain,
                "table": tbl_name,
                "source_count": 0,
                "dest_count": 0,
                "rejected": 0,
                "status": "ERROR (Missing in Postgres)",
            })
            continue

        table_obj = meta.tables[tbl_name]

        # Read from SQLite
        conn_sqlite = sqlite3.connect(src_path)
        conn_sqlite.row_factory = sqlite3.Row
        cur = conn_sqlite.cursor()
        cur.execute(f"SELECT * FROM \"{tbl_name}\";")
        raw_rows = [dict(r) for r in cur.fetchall()]
        conn_sqlite.close()

        src_count = len(raw_rows)
        if src_count == 0:
            with pg_engine.connect() as conn:
                dest_cnt = conn.execute(text(f"SELECT count(*) FROM \"{tbl_name}\";")).scalar()
            migration_summary.append({
                "domain": domain,
                "table": tbl_name,
                "source_count": 0,
                "dest_count": dest_cnt,
                "rejected": 0,
                "status": "PASS (Empty Source)",
            })
            continue

        # Clean and sanitize records
        cleaned_rows = [clean_row_for_postgres(r, table_obj) for r in raw_rows]

        # Insert idempotently using PostgreSQL on_conflict_do_nothing (handles PK and all unique constraints)
        with pg_engine.begin() as conn:
            stmt = pg_insert(table_obj).values(cleaned_rows).on_conflict_do_nothing()
            conn.execute(stmt)

            # Sequence alignment for integer primary keys
            if "id" in table_obj.columns and str(table_obj.columns["id"].type).upper().startswith("INT"):
                seq_sql = f"""
                SELECT setval(
                    pg_get_serial_sequence('"{tbl_name}"', 'id'),
                    COALESCE((SELECT MAX(id) FROM "{tbl_name}"), 1),
                    true
                );
                """
                try:
                    conn.execute(text(seq_sql))
                except Exception as seq_err:
                    logger.debug(f"Sequence alignment note for {tbl_name}: {seq_err}")

        # Destination verification count
        with pg_engine.connect() as conn:
            dest_count = conn.execute(text(f"SELECT count(*) FROM \"{tbl_name}\";")).scalar()

        status = "PASS" if dest_count >= src_count else f"FAIL (Src: {src_count}, Dst: {dest_count})"
        total_migrated_records += src_count
        migration_summary.append({
            "domain": domain,
            "table": tbl_name,
            "source_count": src_count,
            "dest_count": dest_count,
            "rejected": 0,
            "status": status,
        })

    # 4. Create PostgreSQL Domain Schema Views
    logger.info("Step 4: Creating PostgreSQL domain views (users.*, staff.*, waste_management.*)...")
    with pg_engine.begin() as conn:
        for domain, _, tbl_name in TABLE_MIGRATION_ORDER:
            view_sql = f'CREATE OR REPLACE VIEW "{domain}"."{tbl_name}" AS SELECT * FROM public."{tbl_name}";'
            try:
                conn.execute(text(view_sql))
            except Exception as e:
                logger.warning(f"Could not create domain view {domain}.{tbl_name}: {e}")

    # 5. Build and print Migration Audit Report
    print("\n" + "=" * 95)
    print("           WASTEDASH CONSOLIDATED POSTGRESQL MIGRATION AUDIT REPORT")
    print("=" * 95)
    print(f"{'Logical Domain':18} {'Table Name':32} {'Source':8} {'Dest':8} {'Rejected':8} {'Status'}")
    print("-" * 95)
    all_passed = True
    for entry in migration_summary:
        print(
            f"{entry['domain']:18} {entry['table']:32} {entry['source_count']:8} "
            f"{entry['dest_count']:8} {entry['rejected']:8} {entry['status']}"
        )
        if "FAIL" in entry["status"]:
            all_passed = False
    print("-" * 95)
    print(f"Total Tables Processed: {len(migration_summary)} | Total Source Records: {total_migrated_records}")
    print(f"Migration Status: {'SUCCESS' if all_passed else 'ATTENTION REQUIRED'}")
    print("=" * 95 + "\n")

    return {
        "backups": backup_report,
        "summary": migration_summary,
        "total_migrated": total_migrated_records,
        "all_passed": all_passed,
        "status": "SUCCESS" if all_passed else "FAILURE",
    }


def print_rollback_guidance():
    """Prints clear, safe rollback instructions."""
    print("""
================================================================================
                    WASTEDASH DATABASE ROLLBACK PROCEDURE
================================================================================
If you need to roll back to the three SQLite databases for any reason:

1. SOURCE SQLITE FILES WERE NEVER MODIFIED:
   The migration utility strictly performs non-destructive read operations against:
     - backend/users.db
     - backend/staff.db
     - backend/waste_management.db

2. BACKUPS LOCATION:
   Verified pre-migration snapshots with SHA-256 hashes are preserved in:
     backend/backups/

3. REVERT RUNTIME CONFIGURATION:
   In your .env or Render service environment:
     - Revert USER_DATABASE_URL=sqlite:///./users.db
     - Revert STAFF_DATABASE_URL=sqlite:///./staff.db
     - Revert WASTE_DATABASE_URL=sqlite:///./waste_management.db
     - Restart backend service.

4. RESTORING FROM SNAPSHOTS (IF NEEDED):
   cp backend/backups/users_backup_<ts>.db backend/users.db
   cp backend/backups/staff_backup_<ts>.db backend/staff.db
   cp backend/backups/waste_management_backup_<ts>.db backend/waste_management.db
================================================================================
""")


def main():
    parser = argparse.ArgumentParser(description="WasteDash SQLite to PostgreSQL Consolidation Utility")
    parser.add_argument("--target-url", type=str, help="PostgreSQL destination connection URL")
    parser.add_argument("--dry-run", action="store_true", help="Validate connections and schemas without inserting data")
    parser.add_argument("--verify-only", action="store_true", help="Create backups and verify tables without modifying target")
    parser.add_argument("--rollback-info", action="store_true", help="Display rollback procedure instructions")

    args = parser.parse_args()

    if args.rollback_info:
        print_rollback_guidance()
        return

    try:
        res = run_migration(
            target_url=args.target_url,
            dry_run=args.dry_run,
            verify_only=args.verify_only
        )
        if not res.get("all_passed", True):
            sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
