"""osdr schema and table creation

Revision ID: 37d227105faa
Revises: 651fd63e4e65
Create Date: 2026-04-03 19:18:36.610526

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "37d227105faa"
down_revision: Union[str, Sequence[str], None] = "651fd63e4e65"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS stg_osdr")

    op.create_table(
        "datasets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("dataset_accession", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("data_source", sa.Text(), nullable=True),
        sa.Column("organism", sa.Text(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("repository_url", sa.Text(), nullable=True),
        sa.Column(
            "s_ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["s_run_id"], ["tech.run_management.s_run_id"]),
        sa.UniqueConstraint("dataset_accession", name="uq_stg_osdr_datasets"),
        schema="stg_osdr",
    )

    op.create_index(
        "ix_stg_osdr_datasets_run_id",
        "datasets",
        ["s_run_id"],
        unique=False,
        schema="stg_osdr",
    )
    op.create_index(
        "ix_stg_osdr_datasets_accession",
        "datasets",
        ["dataset_accession"],
        unique=False,
        schema="stg_osdr",
    )

    op.create_table(
        "assays",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("assay_accession", sa.Text(), nullable=False),
        sa.Column("dataset_accession", sa.Text(), nullable=True),
        sa.Column("assay_type", sa.Text(), nullable=True),
        sa.Column("technology", sa.Text(), nullable=True),
        sa.Column("platform", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column(
            "s_ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["s_run_id"], ["tech.run_management.s_run_id"]),
        sa.UniqueConstraint("assay_accession", name="uq_stg_osdr_assays"),
        schema="stg_osdr",
    )

    op.create_index(
        "ix_stg_osdr_assays_run_id",
        "assays",
        ["s_run_id"],
        unique=False,
        schema="stg_osdr",
    )
    op.create_index(
        "ix_stg_osdr_assays_accession",
        "assays",
        ["assay_accession"],
        unique=False,
        schema="stg_osdr",
    )
    op.create_index(
        "ix_stg_osdr_assays_dataset_accession",
        "assays",
        ["dataset_accession"],
        unique=False,
        schema="stg_osdr",
    )

    op.create_table(
        "samples",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("sample_accession", sa.Text(), nullable=False),
        sa.Column("dataset_accession", sa.Text(), nullable=True),
        sa.Column("assay_accession", sa.Text(), nullable=True),
        sa.Column("sample_name", sa.Text(), nullable=True),
        sa.Column("organism", sa.Text(), nullable=True),
        sa.Column("tissue", sa.Text(), nullable=True),
        sa.Column("sex", sa.Text(), nullable=True),
        sa.Column("strain", sa.Text(), nullable=True),
        sa.Column(
            "s_ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["s_run_id"], ["tech.run_management.s_run_id"]),
        sa.UniqueConstraint("sample_accession", name="uq_stg_osdr_samples"),
        schema="stg_osdr",
    )

    op.create_index(
        "ix_stg_osdr_samples_run_id",
        "samples",
        ["s_run_id"],
        unique=False,
        schema="stg_osdr",
    )
    op.create_index(
        "ix_stg_osdr_samples_accession",
        "samples",
        ["sample_accession"],
        unique=False,
        schema="stg_osdr",
    )
    op.create_index(
        "ix_stg_osdr_samples_dataset_accession",
        "samples",
        ["dataset_accession"],
        unique=False,
        schema="stg_osdr",
    )
    op.create_index(
        "ix_stg_osdr_samples_assay_accession",
        "samples",
        ["assay_accession"],
        unique=False,
        schema="stg_osdr",
    )

    op.create_table(
        "files",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("file_accession", sa.Text(), nullable=False),
        sa.Column("dataset_accession", sa.Text(), nullable=True),
        sa.Column("assay_accession", sa.Text(), nullable=True),
        sa.Column("sample_accession", sa.Text(), nullable=True),
        sa.Column("file_name", sa.Text(), nullable=True),
        sa.Column("file_type", sa.Text(), nullable=True),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("md5sum", sa.Text(), nullable=True),
        sa.Column(
            "s_ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("s_source_url", sa.Text(), nullable=False),
        sa.Column("s_run_id", sa.BigInteger(), nullable=False),
        sa.Column("s_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["s_run_id"], ["tech.run_management.s_run_id"]),
        sa.UniqueConstraint("file_accession", name="uq_stg_osdr_files"),
        schema="stg_osdr",
    )

    op.create_index(
        "ix_stg_osdr_files_run_id",
        "files",
        ["s_run_id"],
        unique=False,
        schema="stg_osdr",
    )
    op.create_index(
        "ix_stg_osdr_files_accession",
        "files",
        ["file_accession"],
        unique=False,
        schema="stg_osdr",
    )
    op.create_index(
        "ix_stg_osdr_files_dataset_accession",
        "files",
        ["dataset_accession"],
        unique=False,
        schema="stg_osdr",
    )
    op.create_index(
        "ix_stg_osdr_files_assay_accession",
        "files",
        ["assay_accession"],
        unique=False,
        schema="stg_osdr",
    )
    op.create_index(
        "ix_stg_osdr_files_sample_accession",
        "files",
        ["sample_accession"],
        unique=False,
        schema="stg_osdr",
    )


def downgrade() -> None:
    op.drop_index("ix_stg_osdr_files_sample_accession", table_name="files", schema="stg_osdr")
    op.drop_index("ix_stg_osdr_files_assay_accession", table_name="files", schema="stg_osdr")
    op.drop_index("ix_stg_osdr_files_dataset_accession", table_name="files", schema="stg_osdr")
    op.drop_index("ix_stg_osdr_files_accession", table_name="files", schema="stg_osdr")
    op.drop_index("ix_stg_osdr_files_run_id", table_name="files", schema="stg_osdr")
    op.drop_table("files", schema="stg_osdr")

    op.drop_index("ix_stg_osdr_samples_assay_accession", table_name="samples", schema="stg_osdr")
    op.drop_index("ix_stg_osdr_samples_dataset_accession", table_name="samples", schema="stg_osdr")
    op.drop_index("ix_stg_osdr_samples_accession", table_name="samples", schema="stg_osdr")
    op.drop_index("ix_stg_osdr_samples_run_id", table_name="samples", schema="stg_osdr")
    op.drop_table("samples", schema="stg_osdr")

    op.drop_index("ix_stg_osdr_assays_dataset_accession", table_name="assays", schema="stg_osdr")
    op.drop_index("ix_stg_osdr_assays_accession", table_name="assays", schema="stg_osdr")
    op.drop_index("ix_stg_osdr_assays_run_id", table_name="assays", schema="stg_osdr")
    op.drop_table("assays", schema="stg_osdr")

    op.drop_index("ix_stg_osdr_datasets_accession", table_name="datasets", schema="stg_osdr")
    op.drop_index("ix_stg_osdr_datasets_run_id", table_name="datasets", schema="stg_osdr")
    op.drop_table("datasets", schema="stg_osdr")