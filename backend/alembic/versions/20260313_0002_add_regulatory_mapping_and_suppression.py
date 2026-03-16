"""Add regulatory mapping and suppression columns to findings.

Revision ID: 20260313_0002
Revises: 20260311_0001
Create Date: 2026-03-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = "20260313_0002"
down_revision = "20260311_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add regulatory_categories (JSON array) and suppressed (boolean) columns to findings."""
    # Add regulatory_categories as JSON array
    op.add_column(
        "findings",
        sa.Column("regulatory_categories", sa.JSON(), nullable=False, server_default="[]")
    )
    # Add suppressed flag
    op.add_column(
        "findings",
        sa.Column("suppressed", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )


def downgrade() -> None:
    """Remove regulatory_categories and suppressed columns from findings."""
    op.drop_column("findings", "suppressed")
    op.drop_column("findings", "regulatory_categories")
