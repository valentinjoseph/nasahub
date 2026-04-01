"""update id_management for staging row lineage

Revision ID: bee1d46bf816
Revises: 71fcc8f3c61b
Create Date: 2026-04-01 22:24:12.691550

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "bee1d46bf816"
down_revision: Union[str, Sequence[str], None] = "71fcc8f3c61b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_id_management_source_table_record_id",
        "id_management",
        schema="tech",
        type_="unique",
    )

    op.add_column(
        "id_management",
        sa.Column("staging_schema", sa.Text(), nullable=True),
        schema="tech",
    )

    op.add_column(
        "id_management",
        sa.Column("staging_row_id", sa.BigInteger(), nullable=True),
        schema="tech",
    )

    op.create_index(
        "ix_id_management_staging_schema",
        "id_management",
        ["staging_schema"],
        unique=False,
        schema="tech",
    )

    op.create_index(
        "ix_id_management_staging_row_id",
        "id_management",
        ["staging_row_id"],
        unique=False,
        schema="tech",
    )


def downgrade() -> None:
    op.drop_index("ix_id_management_staging_row_id", table_name="id_management", schema="tech")
    op.drop_index("ix_id_management_staging_schema", table_name="id_management", schema="tech")

    op.drop_column("id_management", "staging_row_id", schema="tech")
    op.drop_column("id_management", "staging_schema", schema="tech")

    op.create_unique_constraint(
        "uq_id_management_source_table_record_id",
        "id_management",
        ["source_table", "source_record_id"],
        schema="tech",
    )