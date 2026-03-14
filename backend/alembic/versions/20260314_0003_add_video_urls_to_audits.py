"""Add video_urls column to audits.

Revision ID: 20260314_0003
Revises: 20260313_0002
Create Date: 2026-03-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260314_0003"
down_revision = "20260313_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add video_urls JSON column to audits table (nullable, default null)."""
    op.add_column(
        "audits",
        sa.Column("video_urls", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    """Remove video_urls column from audits table."""
    op.drop_column("audits", "video_urls")
