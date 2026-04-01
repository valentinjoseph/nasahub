"""create tech and staging schemas

Revision ID: aab03d729788
Revises: 09a2019a5eda
Create Date: 2026-04-01 21:58:28.592243
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aab03d729788"
down_revision: Union[str, Sequence[str], None] = "09a2019a5eda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS tech")
    op.execute("CREATE SCHEMA IF NOT EXISTS stg_eonet")
    op.execute("CREATE SCHEMA IF NOT EXISTS stg_neows")

    op.create_table(
        "run_management",
        sa.Column("s_run_id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("source_endpoint", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("run_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("run_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_inserted", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="tech",
    )

    op.create_table(
        "id_management",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True, nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("source_table", sa.Text(), nullable=False),
        sa.Column("source_record_id", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["s_run_id"], ["tech.run_management.s_run_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("source_table", "source_record_id", name="uq_id_management_source_table_record_id"),
        schema="tech",
    )

    op.create_index(
        "ix_run_management_source_name",
        "run_management",
        ["source_name"],
        unique=False,
        schema="tech",
    )
    op.create_index(
        "ix_run_management_source_endpoint",
        "run_management",
        ["source_endpoint"],
        unique=False,
        schema="tech",
    )
    op.create_index(
        "ix_run_management_status",
        "run_management",
        ["status"],
        unique=False,
        schema="tech",
    )

    op.create_index(
        "ix_id_management_source_name",
        "id_management",
        ["source_name"],
        unique=False,
        schema="tech",
    )
    op.create_index(
        "ix_id_management_source_table",
        "id_management",
        ["source_table"],
        unique=False,
        schema="tech",
    )
    op.create_index(
        "ix_id_management_source_record_id",
        "id_management",
        ["source_record_id"],
        unique=False,
        schema="tech",
    )
    op.create_index(
        "ix_id_management_s_run_id",
        "id_management",
        ["s_run_id"],
        unique=False,
        schema="tech",
    )


def downgrade() -> None:
    op.drop_index("ix_id_management_s_run_id", table_name="id_management", schema="tech")
    op.drop_index("ix_id_management_source_record_id", table_name="id_management", schema="tech")
    op.drop_index("ix_id_management_source_table", table_name="id_management", schema="tech")
    op.drop_index("ix_id_management_source_name", table_name="id_management", schema="tech")

    op.drop_index("ix_run_management_status", table_name="run_management", schema="tech")
    op.drop_index("ix_run_management_source_endpoint", table_name="run_management", schema="tech")
    op.drop_index("ix_run_management_source_name", table_name="run_management", schema="tech")

    op.drop_table("id_management", schema="tech")
    op.drop_table("run_management", schema="tech")

    op.execute("DROP SCHEMA IF EXISTS stg_neows CASCADE")
    op.execute("DROP SCHEMA IF EXISTS stg_eonet CASCADE")
    op.execute("DROP SCHEMA IF EXISTS tech CASCADE")