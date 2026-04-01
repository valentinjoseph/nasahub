"""change eonet staging uniqueness for dedupe

Revision ID: 7f5f3f68dc30
Revises: fb07461adb87
Create Date: 2026-04-01 22:49:46.430870

"""
from typing import Sequence, Union

from alembic import op


revision: str = "7f5f3f68dc30"
down_revision: Union[str, Sequence[str], None] = "fb07461adb87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_stg_eonet_events_event_id_run_id",
        "events",
        schema="stg_eonet",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_stg_eonet_events_event_id",
        "events",
        ["event_id"],
        schema="stg_eonet",
    )

    op.drop_constraint(
        "uq_stg_eonet_categories_category_id_run_id",
        "categories",
        schema="stg_eonet",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_stg_eonet_categories_category_id",
        "categories",
        ["category_id"],
        schema="stg_eonet",
    )

    op.drop_constraint(
        "uq_stg_eonet_sources_source_id_run_id",
        "sources",
        schema="stg_eonet",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_stg_eonet_sources_source_id",
        "sources",
        ["source_id"],
        schema="stg_eonet",
    )

    op.drop_constraint(
        "uq_stg_eonet_layers_category_layer_run",
        "layers",
        schema="stg_eonet",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_stg_eonet_layers_category_layer",
        "layers",
        ["category_id", "layer_name"],
        schema="stg_eonet",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_stg_eonet_layers_category_layer",
        "layers",
        schema="stg_eonet",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_stg_eonet_layers_category_layer_run",
        "layers",
        ["category_id", "layer_name", "s_run_id"],
        schema="stg_eonet",
    )

    op.drop_constraint(
        "uq_stg_eonet_sources_source_id",
        "sources",
        schema="stg_eonet",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_stg_eonet_sources_source_id_run_id",
        "sources",
        ["source_id", "s_run_id"],
        schema="stg_eonet",
    )

    op.drop_constraint(
        "uq_stg_eonet_categories_category_id",
        "categories",
        schema="stg_eonet",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_stg_eonet_categories_category_id_run_id",
        "categories",
        ["category_id", "s_run_id"],
        schema="stg_eonet",
    )

    op.drop_constraint(
        "uq_stg_eonet_events_event_id",
        "events",
        schema="stg_eonet",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_stg_eonet_events_event_id_run_id",
        "events",
        ["event_id", "s_run_id"],
        schema="stg_eonet",
    )