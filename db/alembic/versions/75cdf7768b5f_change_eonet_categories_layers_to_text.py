"""change eonet categories layers to text

Revision ID: 75cdf7768b5f
Revises: ef7486a70ab4
Create Date: 2026-04-01 22:31:41.491716

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "75cdf7768b5f"
down_revision: Union[str, Sequence[str], None] = "ef7486a70ab4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "categories",
        "layers",
        schema="stg_eonet",
        existing_type=sa.JSON(),
        type_=sa.Text(),
        postgresql_using="layers::text",
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade not implemented")