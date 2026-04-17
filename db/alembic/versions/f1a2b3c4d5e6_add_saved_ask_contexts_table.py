"""add saved ask contexts table

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-04-16 16:30:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tech.saved_ask_contexts (
            context_id text PRIMARY KEY,
            label text NOT NULL,
            mode text NOT NULL CHECK (mode IN ('entity', 'general')),
            source text NOT NULL CHECK (source IN ('general', 'neows', 'eonet', 'exoplanet', 'osdr')),
            entity_id text NULL,
            comparison_entity_id text NULL,
            question text NOT NULL DEFAULT '',
            include_live_enrichment boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tech.saved_ask_contexts;")
