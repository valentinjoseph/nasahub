import json
import requests
from sqlalchemy import text

from db.session import engine

EONET_CATEGORIES_URL = "https://eonet.gsfc.nasa.gov/api/v3/categories"


def main():
    response = requests.get(EONET_CATEGORIES_URL, timeout=30)
    response.raise_for_status()
    data = response.json()
    categories = data.get("categories", [])

    with engine.begin() as conn:
        run_id = conn.execute(
            text("""
                INSERT INTO tech.run_management (
                    s_run_id,
                    source_name,
                    source_endpoint,
                    status,
                    run_started_at,
                    records_inserted,
                    created_at
                )
                VALUES (
                    (SELECT COALESCE(MAX(s_run_id), 0) + 1 FROM tech.run_management),
                    'eonet',
                    'layers',
                    'pending',
                    now(),
                    0,
                    now()
                )
                RETURNING s_run_id
            """)
        ).scalar_one()

        inserted = 0

        for category in categories:
            layers_url = category.get("layers")
            if not layers_url:
                continue

            layer_response = requests.get(layers_url, timeout=30)
            layer_response.raise_for_status()
            layer_data = layer_response.json()

            response_title = layer_data.get("title")
            response_description = layer_data.get("description")
            endpoint_link = layer_data.get("link")

            response_categories = layer_data.get("categories", [])

            for response_category in response_categories:
                category_id = response_category.get("id")
                category_title = response_category.get("title")
                layers = response_category.get("layers", [])

                for layer in layers:
                    staging_row_id = conn.execute(
                        text("""
                            INSERT INTO stg_eonet.layers (
                                category_id,
                                category_title,
                                layer_name,
                                service_url,
                                service_type_id,
                                parameters,
                                endpoint_link,
                                response_title,
                                response_description,
                                s_ingested_at,
                                s_source_url,
                                s_run_id,
                                s_payload
                            )
                            VALUES (
                                :category_id,
                                :category_title,
                                :layer_name,
                                :service_url,
                                :service_type_id,
                                CAST(:parameters AS jsonb),
                                :endpoint_link,
                                :response_title,
                                :response_description,
                                now(),
                                :s_source_url,
                                :s_run_id,
                                CAST(:s_payload AS jsonb)
                            )
                            ON CONFLICT (category_id, layer_name) DO NOTHING
                            RETURNING id
                        """),
                        {
                            "category_id": category_id,
                            "category_title": category_title,
                            "layer_name": layer.get("name"),
                            "service_url": layer.get("serviceUrl"),
                            "service_type_id": layer.get("serviceTypeId"),
                            "parameters": json.dumps(layer.get("parameters")),
                            "endpoint_link": endpoint_link,
                            "response_title": response_title,
                            "response_description": response_description,
                            "s_source_url": layers_url,
                            "s_run_id": run_id,
                            "s_payload": json.dumps(layer),
                        },
                    ).scalar_one_or_none()

                    if staging_row_id is None:
                        continue

                    conn.execute(
                        text("""
                            INSERT INTO tech.id_management (
                                source_name,
                                source_table,
                                source_record_id,
                                staging_schema,
                                staging_row_id,
                                s_run_id,
                                s_source_url,
                                s_ingested_at
                            )
                            VALUES (
                                :source_name,
                                :source_table,
                                :source_record_id,
                                :staging_schema,
                                :staging_row_id,
                                :s_run_id,
                                :s_source_url,
                                now()
                            )
                        """),
                        {
                            "source_name": "eonet",
                            "source_table": "layers",
                            "source_record_id": f"{category_id}:{layer.get('name')}",
                            "staging_schema": "stg_eonet",
                            "staging_row_id": staging_row_id,
                            "s_run_id": run_id,
                            "s_source_url": layers_url,
                        },
                    )

                    inserted += 1

        conn.execute(
            text("""
                UPDATE tech.run_management
                SET status = 'success',
                    run_finished_at = now(),
                    records_inserted = :records_inserted
                WHERE s_run_id = :s_run_id
            """),
            {"s_run_id": run_id, "records_inserted": inserted},
        )

    print(f"Run {run_id} inserted {inserted} layers")


if __name__ == "__main__":
    main()