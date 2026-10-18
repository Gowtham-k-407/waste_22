"""Consolidate three SQLite databases into single PostgreSQL database with logical domains

Revision ID: c0a1b2c3d4e5
Revises: 2e846b2a149f
Create Date: 2026-10-18 15:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c0a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = '2e846b2a149f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Creates the three logical domain schemas and domain views for PostgreSQL."""
    # 1. Create logical schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS users;")
    op.execute("CREATE SCHEMA IF NOT EXISTS staff;")
    op.execute("CREATE SCHEMA IF NOT EXISTS waste_management;")

    # 2. Create domain views in PostgreSQL (safe, idempotent)
    domain_table_map = {
        "users": [
            "users", "password_reset_tokens", "auth_audit_logs", "user_ai_references"
        ],
        "staff": [
            "staff_profiles", "staff_duty_assignments", "staff_audit_logs"
        ],
        "waste_management": [
            "zones", "wards", "waste_categories", "waste_records", "segregation_plants",
            "collection_vehicles", "ai_detections", "image_contributions", "uploads",
            "dataset_images", "ai_models", "training_jobs", "dataset_sources",
            "dataset_imports", "environmental_metrics", "operational_alerts",
            "optimization_recommendations", "iot_devices", "device_telemetry",
            "iot_sorting_records", "public_complaints", "complaint_follow_ups",
            "notifications", "weighbridge_records", "simulation_runs", "ai_inference_audit"
        ]
    }

    # In online mode with a PostgreSQL connection, create the domain views
    conn = op.get_bind()
    if conn and "postgresql" in conn.dialect.name:
        for domain, tables in domain_table_map.items():
            for tbl in tables:
                op.execute(
                    f'CREATE OR REPLACE VIEW "{domain}"."{tbl}" AS SELECT * FROM public."{tbl}";'
                )


def downgrade() -> None:
    """Drops the logical domain schemas and views."""
    conn = op.get_bind()
    if conn and "postgresql" in conn.dialect.name:
        op.execute("DROP SCHEMA IF EXISTS users CASCADE;")
        op.execute("DROP SCHEMA IF EXISTS staff CASCADE;")
        op.execute("DROP SCHEMA IF EXISTS waste_management CASCADE;")
