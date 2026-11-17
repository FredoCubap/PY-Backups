"""registro de PC: workers, devices, device_macs, enroll_codes

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(64, collation="NOCASE"), nullable=False, unique=True),
        sa.Column("created_at", sa.String(32), nullable=False),
    )
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.String(32), nullable=False),
        sa.Column("revoked_at", sa.String(32)),
    )
    op.create_table(
        "device_macs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("mac", sa.String(17), nullable=False, unique=True),
    )
    op.create_table(
        "enroll_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.String(32), nullable=False),
        sa.Column("used_at", sa.String(32)),
    )


def downgrade() -> None:
    op.drop_table("enroll_codes")
    op.drop_table("device_macs")
    op.drop_table("devices")
    op.drop_table("workers")
