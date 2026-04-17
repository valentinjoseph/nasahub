"""add pinned entities table

Revision ID: f7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-04-16 17:10:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "f7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tech.pinned_entities (
            pin_id text PRIMARY KEY,
            source text NOT NULL CHECK (source IN ('neows', 'eonet', 'exoplanet', 'osdr')),
            entity_id text NOT NULL,
            label text NOT NULL,
            watchlist boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tech.pinned_entities;")
