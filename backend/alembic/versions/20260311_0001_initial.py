"""Initial EthicalSiteInspector schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260311_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("trust_score", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=True),
        sa.Column("selected_scenarios", sa.JSON(), nullable=False),
        sa.Column("selected_personas", sa.JSON(), nullable=False),
        sa.Column("report_path", sa.String(length=2048), nullable=True),
        sa.Column("report_public_url", sa.String(length=2048), nullable=True),
        sa.Column("raw_run", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("audit_id", sa.String(length=36), nullable=False),
        sa.Column("phase", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["audit_id"], ["audits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_events_audit_id"), "audit_events", ["audit_id"], unique=False)
    op.create_table(
        "findings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("audit_id", sa.String(length=36), nullable=False),
        sa.Column("scenario", sa.String(length=50), nullable=False),
        sa.Column("persona", sa.String(length=50), nullable=False),
        sa.Column("pattern_family", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.Column("evidence_excerpt", sa.Text(), nullable=False),
        sa.Column("rule_reason", sa.Text(), nullable=False),
        sa.Column("evidence_payload", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("trust_impact", sa.Float(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["audit_id"], ["audits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_findings_audit_id"), "findings", ["audit_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_findings_audit_id"), table_name="findings")
    op.drop_table("findings")
    op.drop_index(op.f("ix_audit_events_audit_id"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("audits")
