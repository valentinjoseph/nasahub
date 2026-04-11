from pathlib import Path
from datetime import date, datetime, timezone
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from api.main import (
    DASHBOARD_INDEX,
    FRONTEND_DIR,
    app,
    build_access_log_payload,
    get_request_id,
    health,
    health_live,
    health_ready,
    path_requires_auth,
    request_has_valid_auth,
)
from api.schemas import AskNasaHubRequest
from api.routes.analytics import (
    ANALYTICS_ENDPOINTS,
    ask_nasahub,
    get_analytics_catalog,
    get_eonet_event_detail,
    get_eonet_event_insight,
    get_exoplanet_planet_detail,
    get_exoplanet_planet_insight,
    infer_general_intent,
    infer_general_source,
    list_eonet_category_summary,
    list_eonet_event_overview,
    list_exoplanet_catalog,
    list_exoplanet_discovery_method_summary,
    list_exoplanet_discovery_yearly_summary,
    search_exoplanet_planets,
    list_ingestion_status,
    get_neows_object_insight,
    list_neows_object_approaches,
    list_neows_daily_summary,
    get_neows_object_live_enrichment,
    get_neows_object_detail,
    search_neows_objects,
    list_neows_kpis,
    list_osdr_assay_type_summary,
    list_osdr_dataset_summary,
    list_osdr_datasets,
)


class FakeResult:
    def __init__(self, rows=None, scalar_value=None):
        self._rows = rows
        self._scalar_value = scalar_value

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar_one(self):
        return self._scalar_value


class FakeSession:
    def __init__(self, rows=None, scalar_values=None):
        self.rows = rows or []
        self.scalar_values = list(scalar_values or [])
        self.queries = []
        self.params = []

    def execute(self, statement, params=None):
        self.queries.append(str(statement))
        self.params.append(params)
        normalized = str(statement).strip().upper()
        if normalized.startswith("SELECT COUNT(*)"):
            return FakeResult(scalar_value=self.scalar_values.pop(0))
        return FakeResult(rows=self.rows)


class AnalyticsRoutesTestCase(unittest.TestCase):
    def test_infer_general_source_prefers_neows_for_asteroid_question(self):
        self.assertEqual(
            infer_general_source("Which is the biggest asteroid that got close to Earth?"),
            "neows",
        )

    def test_infer_general_intent_detects_source_specific_ranking(self):
        self.assertEqual(
            infer_general_intent("neows", "Which is the fastest object in the database?"),
            "fastest",
        )
        self.assertEqual(
            infer_general_intent("eonet", "What are the latest open events right now?"),
            "open",
        )
        self.assertEqual(
            infer_general_intent("exoplanet", "Which are the nearest planets in the catalog?"),
            "nearest",
        )

    def test_openapi_registers_analytics_routes_with_response_models(self):
        openapi = app.openapi()
        analytics_paths = {
            path
            for path in openapi["paths"]
            if path.startswith("/analytics/")
        }
        self.assertEqual(
            analytics_paths,
            {
                "/analytics/catalog",
                "/analytics/ingestion-status",
                "/analytics/neows/daily-summary",
                "/analytics/neows/kpis",
                "/analytics/neows/object/{neo_reference_id}",
                "/analytics/neows/objects",
                "/analytics/neows/object/{neo_reference_id}/live-enrichment",
                "/analytics/neows/object/{neo_reference_id}/approaches",
                "/analytics/neows/object/{neo_reference_id}/insight",
                "/analytics/eonet/event/{event_id}",
                "/analytics/eonet/event/{event_id}/insight",
                "/analytics/eonet/category-summary",
                "/analytics/eonet/event-overview",
                "/analytics/exoplanet/discovery-yearly-summary",
                "/analytics/exoplanet/discovery-method-summary",
                "/analytics/exoplanet/catalog",
                "/analytics/exoplanet/planets",
                "/analytics/exoplanet/planet/{pl_name}",
                "/analytics/exoplanet/planet/{pl_name}/insight",
                "/analytics/osdr/dataset-summary",
                "/analytics/osdr/assay-type-summary",
                "/analytics/osdr/datasets",
                "/analytics/ask",
            },
        )
        ingestion_status = openapi["paths"]["/analytics/ingestion-status"]["get"]
        analytics_catalog = openapi["paths"]["/analytics/catalog"]["get"]
        daily_summary = openapi["paths"]["/analytics/neows/daily-summary"]["get"]
        kpis = openapi["paths"]["/analytics/neows/kpis"]["get"]
        neows_object_detail = openapi["paths"]["/analytics/neows/object/{neo_reference_id}"]["get"]
        neows_objects = openapi["paths"]["/analytics/neows/objects"]["get"]
        neows_live_enrichment = openapi["paths"]["/analytics/neows/object/{neo_reference_id}/live-enrichment"]["get"]
        neows_approaches = openapi["paths"]["/analytics/neows/object/{neo_reference_id}/approaches"]["get"]
        neows_insight = openapi["paths"]["/analytics/neows/object/{neo_reference_id}/insight"]["get"]
        eonet_event_detail = openapi["paths"]["/analytics/eonet/event/{event_id}"]["get"]
        eonet_event_insight = openapi["paths"]["/analytics/eonet/event/{event_id}/insight"]["get"]
        eonet_category_summary = openapi["paths"]["/analytics/eonet/category-summary"]["get"]
        eonet_event_overview = openapi["paths"]["/analytics/eonet/event-overview"]["get"]
        exoplanet_yearly = openapi["paths"]["/analytics/exoplanet/discovery-yearly-summary"]["get"]
        exoplanet_method = openapi["paths"]["/analytics/exoplanet/discovery-method-summary"]["get"]
        exoplanet_catalog = openapi["paths"]["/analytics/exoplanet/catalog"]["get"]
        exoplanet_planets = openapi["paths"]["/analytics/exoplanet/planets"]["get"]
        exoplanet_planet_detail = openapi["paths"]["/analytics/exoplanet/planet/{pl_name}"]["get"]
        exoplanet_planet_insight = openapi["paths"]["/analytics/exoplanet/planet/{pl_name}/insight"]["get"]
        osdr_dataset_summary = openapi["paths"]["/analytics/osdr/dataset-summary"]["get"]
        osdr_assay_type_summary = openapi["paths"]["/analytics/osdr/assay-type-summary"]["get"]
        osdr_datasets = openapi["paths"]["/analytics/osdr/datasets"]["get"]
        ask_nasahub_route = openapi["paths"]["/analytics/ask"]["post"]

        self.assertEqual(
            analytics_catalog["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/AnalyticsCatalogResponse",
        )
        self.assertEqual(
            ingestion_status["responses"]["200"]["content"]["application/json"]["schema"][
                "items"
            ]["$ref"],
            "#/components/schemas/IngestionStatusResponse",
        )
        self.assertEqual(
            daily_summary["responses"]["200"]["content"]["application/json"]["schema"][
                "items"
            ]["$ref"],
            "#/components/schemas/NeoWsDailySummaryResponse",
        )
        self.assertEqual(
            kpis["responses"]["200"]["content"]["application/json"]["schema"]["items"][
                "$ref"
            ],
            "#/components/schemas/NeoWsKpiResponse",
        )
        self.assertEqual(
            neows_object_detail["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/NeoWsObjectDetailResponse",
        )
        self.assertEqual(
            neows_objects["responses"]["200"]["content"]["application/json"]["schema"][
                "items"
            ]["$ref"],
            "#/components/schemas/NeoWsObjectSearchResultResponse",
        )
        self.assertEqual(
            neows_live_enrichment["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/NeoWsLiveEnrichmentResponse",
        )
        self.assertEqual(
            neows_approaches["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/NeoWsApproachPageResponse",
        )
        self.assertEqual(
            neows_insight["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/NeoWsInsightResponse",
        )
        self.assertEqual(
            eonet_event_detail["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/EonetEventDetailResponse",
        )
        self.assertEqual(
            eonet_event_insight["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/EonetInsightResponse",
        )
        self.assertEqual(
            eonet_category_summary["responses"]["200"]["content"]["application/json"][
                "schema"
            ]["items"]["$ref"],
            "#/components/schemas/EonetCategorySummaryResponse",
        )
        self.assertEqual(
            eonet_event_overview["responses"]["200"]["content"]["application/json"][
                "schema"
            ]["$ref"],
            "#/components/schemas/EonetEventOverviewPageResponse",
        )
        self.assertEqual(
            exoplanet_yearly["responses"]["200"]["content"]["application/json"]["schema"][
                "items"
            ]["$ref"],
            "#/components/schemas/ExoplanetDiscoveryYearlySummaryResponse",
        )
        self.assertEqual(
            exoplanet_method["responses"]["200"]["content"]["application/json"]["schema"][
                "items"
            ]["$ref"],
            "#/components/schemas/ExoplanetDiscoveryMethodSummaryResponse",
        )
        self.assertEqual(
            exoplanet_catalog["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/ExoplanetCatalogPageResponse",
        )
        self.assertEqual(
            exoplanet_planets["responses"]["200"]["content"]["application/json"]["schema"][
                "items"
            ]["$ref"],
            "#/components/schemas/ExoplanetPlanetSearchResultResponse",
        )
        self.assertEqual(
            exoplanet_planet_detail["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/ExoplanetPlanetDetailResponse",
        )
        self.assertEqual(
            exoplanet_planet_insight["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/ExoplanetInsightResponse",
        )
        self.assertEqual(
            osdr_dataset_summary["responses"]["200"]["content"]["application/json"]["schema"][
                "items"
            ]["$ref"],
            "#/components/schemas/OsdrDatasetSummaryResponse",
        )
        self.assertEqual(
            osdr_assay_type_summary["responses"]["200"]["content"]["application/json"]["schema"][
                "items"
            ]["$ref"],
            "#/components/schemas/OsdrAssayTypeSummaryResponse",
        )
        self.assertEqual(
            osdr_datasets["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/OsdrDatasetCatalogPageResponse",
        )
        self.assertEqual(
            ask_nasahub_route["responses"]["200"]["content"]["application/json"]["schema"][
                "$ref"
            ],
            "#/components/schemas/AskNasaHubResponse",
        )
        parameters = {
            parameter["name"]: parameter["schema"]
            for parameter in eonet_event_overview["parameters"]
        }
        self.assertEqual(parameters["limit"]["default"], 100)
        self.assertEqual(parameters["offset"]["default"], 0)
        self.assertEqual(parameters["category_id"]["anyOf"][0]["type"], "string")
        self.assertEqual(
            parameters["event_status"]["anyOf"][0]["pattern"], "^(open|closed)$"
        )
        exoplanet_parameters = {
            parameter["name"]: parameter["schema"]
            for parameter in exoplanet_catalog["parameters"]
        }
        self.assertEqual(exoplanet_parameters["limit"]["default"], 100)
        self.assertEqual(exoplanet_parameters["offset"]["default"], 0)
        self.assertEqual(exoplanet_parameters["discovery_method"]["anyOf"][0]["type"], "string")
        self.assertEqual(exoplanet_parameters["disc_year"]["anyOf"][0]["type"], "integer")
        osdr_parameters = {
            parameter["name"]: parameter["schema"]
            for parameter in osdr_datasets["parameters"]
        }
        self.assertEqual(osdr_parameters["limit"]["default"], 100)
        self.assertEqual(osdr_parameters["offset"]["default"], 0)
        self.assertEqual(osdr_parameters["data_source"]["anyOf"][0]["type"], "string")
        self.assertEqual(osdr_parameters["dataset_accession"]["anyOf"][0]["type"], "string")

    def test_exoplanet_catalog_query_casts_nullable_disc_year_parameter(self):
        db = FakeSession(
            rows=[
                {
                    "pl_name": "Kepler-22 b",
                    "hostname": "Kepler-22",
                    "discovery_method": "Transit",
                    "disc_year": 2011,
                    "disc_facility": "Kepler",
                    "sy_dist": 195.0,
                    "pl_orbper": 289.9,
                    "pl_rade": 2.4,
                    "pl_bmasse": None,
                    "st_teff": 5518.0,
                    "last_ingested_at": datetime(2026, 4, 10, tzinfo=timezone.utc),
                }
            ],
            scalar_values=[1],
        )

        payload = list_exoplanet_catalog(db=db)

        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["pl_name"], "Kepler-22 b")
        self.assertTrue(any("CAST(:disc_year AS integer) IS NULL" in query for query in db.queries))
        self.assertTrue(any("c.disc_year = CAST(:disc_year AS integer)" in query for query in db.queries))

    def test_health_live_does_not_depend_on_database(self):
        self.assertEqual(
            health_live(),
            {
                "status": "ok",
                "database": "unknown",
            },
        )

    def test_health_ready_reports_database_success(self):
        with patch("api.main.database_ready", return_value=True):
            self.assertEqual(
                health_ready(),
                {
                    "status": "ok",
                    "database": "ok",
                },
            )
            self.assertEqual(health(), {"status": "ok", "database": "ok"})

    def test_health_ready_reports_database_failure(self):
        with patch("api.main.database_ready", return_value=False):
            self.assertEqual(
                health_ready(),
                {
                    "status": "degraded",
                    "database": "error",
                },
            )

    def test_health_paths_are_exempt_from_auth(self):
        self.assertFalse(path_requires_auth("/"))
        self.assertFalse(path_requires_auth("/dashboard"))
        self.assertFalse(path_requires_auth("/dashboard-assets/dashboard.js"))
        self.assertFalse(path_requires_auth("/health"))
        self.assertFalse(path_requires_auth("/health/live"))
        self.assertFalse(path_requires_auth("/health/ready"))
        self.assertTrue(path_requires_auth("/analytics/catalog"))
        self.assertTrue(path_requires_auth("/docs"))

    def test_request_has_valid_auth_supports_api_key_and_bearer(self):
        expected_token = "secret-token"

        self.assertTrue(
            request_has_valid_auth({"x-api-key": "secret-token"}, expected_token)
        )
        self.assertTrue(
            request_has_valid_auth(
                {"authorization": "Bearer secret-token"},
                expected_token,
            )
        )
        self.assertFalse(
            request_has_valid_auth({"x-api-key": "wrong-token"}, expected_token)
        )
        self.assertFalse(
            request_has_valid_auth({"authorization": "Bearer wrong-token"}, expected_token)
        )
        self.assertFalse(request_has_valid_auth({}, expected_token))

    def test_get_request_id_reuses_header_or_generates_one(self):
        self.assertEqual(
            get_request_id({"x-request-id": "req-123"}),
            "req-123",
        )
        generated = get_request_id({})
        self.assertTrue(generated)
        self.assertIsInstance(generated, str)

    def test_build_access_log_payload_is_structured_and_rounded(self):
        payload = build_access_log_payload(
            request_id="req-123",
            method="GET",
            path="/analytics/catalog",
            status_code=200,
            duration_ms=12.3456,
        )

        self.assertEqual(
            payload,
            {
                "request_id": "req-123",
                "method": "GET",
                "path": "/analytics/catalog",
                "status_code": 200,
                "duration_ms": 12.35,
            },
        )

    def test_dashboard_files_exist(self):
        self.assertTrue(FRONTEND_DIR.exists())
        self.assertTrue(DASHBOARD_INDEX.exists())
        self.assertTrue((Path(FRONTEND_DIR) / "dashboard.css").exists())
        self.assertTrue((Path(FRONTEND_DIR) / "dashboard.js").exists())

    def test_analytics_catalog_lists_known_endpoints(self):
        response = get_analytics_catalog()

        self.assertEqual(response, {"endpoints": ANALYTICS_ENDPOINTS})
        self.assertEqual(response["endpoints"][0].path, "/analytics/ingestion-status")
        paginated_endpoints = [endpoint for endpoint in response["endpoints"] if endpoint.paginated]
        self.assertTrue(paginated_endpoints)
        self.assertIn("limit", paginated_endpoints[0].filters)

    def test_page_response_models_expose_standard_pagination_fields(self):
        schemas = app.openapi()["components"]["schemas"]

        for schema_name in (
            "EonetEventOverviewPageResponse",
            "ExoplanetCatalogPageResponse",
            "OsdrDatasetCatalogPageResponse",
        ):
            properties = schemas[schema_name]["properties"]
            self.assertEqual(set(properties), {"items", "total", "limit", "offset"})
            self.assertEqual(properties["items"]["type"], "array")
            self.assertEqual(properties["total"]["type"], "integer")
            self.assertEqual(properties["limit"]["type"], "integer")
            self.assertEqual(properties["offset"]["type"], "integer")
        catalog_properties = schemas["AnalyticsCatalogResponse"]["properties"]
        self.assertEqual(set(catalog_properties), {"endpoints"})

    def test_list_ingestion_status_returns_rows_from_view(self):
        rows = [
            {
                "source_name": "neows",
                "source_endpoint": "feed",
                "latest_run_started_at": datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
                "latest_run_finished_at": datetime(2026, 4, 10, 18, 5, tzinfo=timezone.utc),
                "latest_status": "success",
                "latest_records_inserted": 42,
                "created_at": datetime(2026, 4, 10, 18, 5, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows)

        response = list_ingestion_status(db=db)

        self.assertEqual(response, rows)
        self.assertIn("FROM dmt_generic.v_dmt_ingestion_status", db.queries[0])

    def test_list_neows_daily_summary_returns_rows_from_view(self):
        rows = [
            {
                "close_approach_date": date(2026, 4, 10),
                "neo_count": 10,
                "hazardous_count": 1,
                "distinct_object_count": 10,
                "avg_velocity_km_per_hour": 12345.6,
                "min_miss_distance_kilometers": 1000.0,
                "max_miss_distance_kilometers": 2000.0,
                "biggest_estimated_diameter_max_km": 0.42,
            }
        ]
        db = FakeSession(rows=rows)

        response = list_neows_daily_summary(db=db)

        self.assertEqual(response, rows)
        self.assertIn("FROM dmt_generic.v_dmt_neows_daily_summary", db.queries[0])

    def test_list_neows_kpis_returns_rows_from_view(self):
        rows = [
            {
                "category": "fastest_object_kph",
                "object_id": "12345",
                "object_name": "Asteroid X",
                "est_max_diameter_m": 12.5,
                "velocity_kph": 65432.1,
                "recent_approach_date": date(2026, 4, 10),
                "is_hazardous_flag": False,
                "miss_distance_km": 98765.4,
                "value": 65432.1,
            }
        ]
        db = FakeSession(rows=rows)

        response = list_neows_kpis(db=db)

        self.assertEqual(response, rows)
        self.assertIn("FROM dmt_generic.v_dmt_neows_kpis", db.queries[0])

    def test_get_neows_object_detail_returns_row(self):
        rows = [
            {
                "neo_reference_id": "3542519",
                "name": "(2010 PK9)",
                "nasa_jpl_url": "https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=3542519",
                "absolute_magnitude_h": 20.5,
                "is_potentially_hazardous_asteroid": False,
                "is_sentry_object": False,
                "estimated_diameter_min_km": 0.21,
                "estimated_diameter_max_km": 0.47,
                "first_close_approach_date": date(2026, 4, 1),
                "most_recent_close_approach_date": date(2026, 4, 9),
                "approach_count": 4,
                "min_miss_distance_km": 512345.0,
                "max_velocity_kph": 45678.0,
                "latest_orbiting_body": "Earth",
                "last_ingested_at": datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows)

        response = get_neows_object_detail("3542519", db=db)

        self.assertEqual(response, rows[0])
        self.assertIn("FROM best_identity i", db.queries[0])
        self.assertEqual(db.params[0], {"neo_reference_id": "3542519"})

    def test_search_neows_objects_returns_rows(self):
        rows = [
            {
                "neo_reference_id": "3542519",
                "name": "(2010 PK9)",
                "is_potentially_hazardous_asteroid": True,
                "most_recent_close_approach_date": date(2026, 4, 9),
                "approach_count": 4,
            }
        ]
        db = FakeSession(rows=rows)

        response = search_neows_objects(query="PK9", limit=5, db=db)

        self.assertEqual(response, rows)
        self.assertIn("FROM latest_objects o", db.queries[0])
        self.assertEqual(
            db.params[0],
            {
                "query": "PK9",
                "search_pattern": "%PK9%",
                "prefix_pattern": "PK9%",
                "limit": 5,
            },
        )

    def test_get_neows_object_live_enrichment_returns_payload(self):
        class FakeResponse:
            status_code = 200
            url = "https://api.nasa.gov/neo/rest/v1/neo/3542519?api_key=test-key"

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "neo_reference_id": "3542519",
                    "name": "(2010 PK9)",
                    "nasa_jpl_url": "https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=3542519",
                    "absolute_magnitude_h": 21.81,
                    "is_potentially_hazardous_asteroid": True,
                    "estimated_diameter": {
                        "kilometers": {
                            "estimated_diameter_min": 0.115,
                            "estimated_diameter_max": 0.258,
                        }
                    },
                    "close_approach_data": [
                        {
                            "close_approach_date": "2026-04-09",
                            "orbiting_body": "Earth",
                            "relative_velocity": {"kilometers_per_hour": "45678.1"},
                            "miss_distance": {"kilometers": "512345.6"},
                        }
                    ],
                }

        with patch("api.routes.analytics.NASA_API_KEY", "test-key"):
            with patch("api.routes.analytics.requests.get", return_value=FakeResponse()):
                payload = get_neows_object_live_enrichment("3542519")

        self.assertEqual(payload["neo_reference_id"], "3542519")
        self.assertEqual(payload["source"], "nasa_neows_live")
        self.assertEqual(payload["latest_orbiting_body"], "Earth")
        self.assertIn("Near-Earth Object", payload["generated_summary"])

    def test_list_neows_object_approaches_returns_paginated_rows(self):
        rows = [
            {
                "close_approach_date": date(2026, 4, 9),
                "close_approach_datetime": datetime(2026, 4, 9, 12, 30, tzinfo=timezone.utc),
                "orbiting_body": "Earth",
                "relative_velocity_km_per_hour": 45678.0,
                "miss_distance_kilometers": 512345.0,
                "estimated_diameter_max_km": 0.258,
                "is_potentially_hazardous_asteroid": True,
                "s_ingested_at": datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows, scalar_values=[1])

        response = list_neows_object_approaches("3542519", limit=6, offset=12, db=db)

        self.assertEqual(
            response,
            {
                "items": rows,
                "total": 1,
                "limit": 6,
                "offset": 12,
            },
        )
        self.assertIn("FROM stg_neows.neo_feed", db.queries[1])
        self.assertEqual(
            db.params[1],
            {"neo_reference_id": "3542519", "limit": 6, "offset": 12},
        )

    def test_get_neows_object_insight_returns_local_overview(self):
        rows = [
            {
                "neo_reference_id": "3542519",
                "name": "(2010 PK9)",
                "nasa_jpl_url": None,
                "absolute_magnitude_h": 20.5,
                "is_potentially_hazardous_asteroid": False,
                "is_sentry_object": False,
                "estimated_diameter_min_km": 0.21,
                "estimated_diameter_max_km": 0.47,
                "first_close_approach_date": date(2026, 4, 1),
                "most_recent_close_approach_date": date(2026, 4, 9),
                "approach_count": 4,
                "min_miss_distance_km": 512345.0,
                "max_velocity_kph": 45678.0,
                "latest_orbiting_body": "Earth",
                "last_ingested_at": datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows)

        response = get_neows_object_insight("3542519", mode="overview", db=db)

        self.assertEqual(response["neo_reference_id"], "3542519")
        self.assertEqual(response["mode"], "overview")
        self.assertEqual(response["sources"], ["nasahub_local"])
        self.assertIn("curated local analytics layer", response["summary"])

    def test_get_eonet_event_detail_returns_row(self):
        rows = [
            {
                "event_id": "EONET_19374",
                "title": "Sample Event",
                "description": "Example",
                "link": "https://example.test/event",
                "event_status": "open",
                "closed_at": None,
                "category_count": 1,
                "category_titles": "Wildfires",
                "source_count": 2,
                "source_titles": "NASA, NOAA",
                "geometry_count": 3,
                "latest_geometry_at": datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
                "last_ingested_at": datetime(2026, 4, 10, 12, 5, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows)

        response = get_eonet_event_detail("EONET_19374", db=db)

        self.assertEqual(response, rows[0])
        self.assertIn("WITH latest_event AS", db.queries[0])

    def test_get_eonet_event_insight_returns_row(self):
        rows = [
            {
                "event_id": "EONET_19374",
                "title": "Sample Event",
                "description": "Example",
                "link": "https://example.test/event",
                "event_status": "open",
                "closed_at": None,
                "category_count": 1,
                "category_titles": "Wildfires",
                "source_count": 2,
                "source_titles": "NASA, NOAA",
                "geometry_count": 3,
                "latest_geometry_at": datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
                "last_ingested_at": datetime(2026, 4, 10, 12, 5, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows)

        response = get_eonet_event_insight("EONET_19374", mode="overview", db=db)

        self.assertEqual(response["event_id"], "EONET_19374")
        self.assertEqual(response["mode"], "overview")
        self.assertIn("curated EONET event view", response["summary"])

    def test_list_eonet_category_summary_returns_rows_from_view(self):
        rows = [
            {
                "category_id": "wildfires",
                "category_title": "Wildfires",
                "total_events": 8,
                "open_events": 6,
                "closed_events": 2,
                "total_sources": 8,
                "latest_geometry_at": datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
                "last_ingested_at": datetime(2026, 4, 10, 12, 5, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows)

        response = list_eonet_category_summary(db=db)

        self.assertEqual(response, rows)
        self.assertIn("FROM dmt_generic.v_dmt_eonet_category_summary", db.queries[0])

    def test_list_eonet_event_overview_returns_paginated_rows_with_filters(self):
        rows = [
            {
                "event_id": "EONET_19374",
                "title": "Sample Event",
                "description": "Example",
                "link": "https://example.test/event",
                "event_status": "open",
                "closed_at": None,
                "category_count": 1,
                "category_titles": "Wildfires",
                "source_count": 1,
                "geometry_count": 1,
                "latest_geometry_at": datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
                "last_ingested_at": datetime(2026, 4, 10, 12, 5, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows, scalar_values=[1])

        response = list_eonet_event_overview(
            limit=25,
            offset=50,
            category_id="wildfires",
            event_status="open",
            db=db,
        )

        self.assertEqual(
            response,
            {
                "items": rows,
                "total": 1,
                "limit": 25,
                "offset": 50,
            },
        )
        self.assertIn("COUNT(*)", db.queries[0])
        self.assertIn("FROM dmt_generic.v_dmt_eonet_event_overview", db.queries[1])
        self.assertIn("cat.value ->> 'id' = CAST(:category_id AS text)", db.queries[0])
        self.assertIn("v.event_status = CAST(:event_status AS text)", db.queries[1])
        self.assertEqual(
            db.params[0],
            {
                "limit": 25,
                "offset": 50,
                "category_id": "wildfires",
                "event_status": "open",
            },
        )
        self.assertEqual(db.params[1], db.params[0])

    def test_list_exoplanet_discovery_yearly_summary_returns_rows_from_view(self):
        rows = [
            {
                "disc_year": 2025,
                "planet_count": 100,
                "distinct_host_count": 80,
                "avg_distance_pc": 42.5,
                "cumulative_planet_count": 6000,
            }
        ]
        db = FakeSession(rows=rows)

        response = list_exoplanet_discovery_yearly_summary(db=db)

        self.assertEqual(response, rows)
        self.assertIn(
            "FROM dmt_generic.v_dmt_exoplanet_discovery_yearly_summary",
            db.queries[0],
        )

    def test_list_exoplanet_discovery_method_summary_returns_rows_from_view(self):
        rows = [
            {
                "discovery_method": "Transit",
                "planet_count": 4520,
                "distinct_host_count": 3000,
                "first_disc_year": 2002,
                "last_disc_year": 2026,
                "avg_distance_pc": 700.5,
            }
        ]
        db = FakeSession(rows=rows)

        response = list_exoplanet_discovery_method_summary(db=db)

        self.assertEqual(response, rows)
        self.assertIn(
            "FROM dmt_generic.v_dmt_exoplanet_discovery_method_summary",
            db.queries[0],
        )

    def test_list_exoplanet_catalog_returns_paginated_rows_with_filters(self):
        rows = [
            {
                "pl_name": "Proxima Cen b",
                "hostname": "Proxima Cen",
                "discovery_method": "Radial Velocity",
                "disc_year": 2016,
                "disc_facility": "ESO",
                "sy_dist": 1.30119,
                "pl_orbper": 11.2,
                "pl_rade": 1.02,
                "pl_bmasse": 1.055,
                "st_teff": 3042.0,
                "last_ingested_at": datetime(2026, 4, 10, 12, 5, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows, scalar_values=[1])

        response = list_exoplanet_catalog(
            limit=10,
            offset=20,
            discovery_method="Radial Velocity",
            disc_year=2016,
            db=db,
        )

        self.assertEqual(
            response,
            {
                "items": rows,
                "total": 1,
                "limit": 10,
                "offset": 20,
            },
        )
        self.assertIn("FROM dmt_generic.v_dmt_exoplanet_catalog c", db.queries[1])
        self.assertIn("c.discovery_method = CAST(:discovery_method AS text)", db.queries[0])
        self.assertIn("c.disc_year = CAST(:disc_year AS integer)", db.queries[1])
        self.assertEqual(
            db.params[0],
            {
                "limit": 10,
                "offset": 20,
                "discovery_method": "Radial Velocity",
                "disc_year": 2016,
            },
        )

    def test_search_exoplanet_planets_returns_rows(self):
        rows = [
            {
                "pl_name": "Kepler-22 b",
                "hostname": "Kepler-22",
                "discovery_method": "Transit",
                "disc_year": 2011,
                "sy_dist": 195.4,
            }
        ]
        db = FakeSession(rows=rows)

        response = search_exoplanet_planets(query="Kepler", limit=4, db=db)

        self.assertEqual(response, rows)
        self.assertIn("FROM dmt_generic.v_dmt_exoplanet_catalog", db.queries[0])
        self.assertEqual(
            db.params[0],
            {
                "query": "Kepler",
                "search_pattern": "%Kepler%",
                "prefix_pattern": "Kepler%",
                "limit": 4,
            },
        )

    def test_get_exoplanet_planet_detail_returns_row(self):
        rows = [
            {
                "pl_name": "Kepler-22 b",
                "hostname": "Kepler-22",
                "discovery_method": "Transit",
                "disc_year": 2011,
                "disc_facility": "Kepler",
                "sy_dist": 195.4,
                "pl_orbper": 289.9,
                "pl_rade": 2.4,
                "pl_bmasse": None,
                "st_teff": 5518.0,
                "last_ingested_at": datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows)

        response = get_exoplanet_planet_detail("Kepler-22 b", db=db)

        self.assertEqual(response, rows[0])
        self.assertIn("WHERE pl_name = :pl_name", db.queries[0])

    def test_get_exoplanet_planet_insight_returns_row(self):
        rows = [
            {
                "pl_name": "Kepler-22 b",
                "hostname": "Kepler-22",
                "discovery_method": "Transit",
                "disc_year": 2011,
                "disc_facility": "Kepler",
                "sy_dist": 195.4,
                "pl_orbper": 289.9,
                "pl_rade": 2.4,
                "pl_bmasse": None,
                "st_teff": 5518.0,
                "last_ingested_at": datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows)

        response = get_exoplanet_planet_insight("Kepler-22 b", mode="overview", db=db)

        self.assertEqual(response["pl_name"], "Kepler-22 b")
        self.assertEqual(response["mode"], "overview")
        self.assertIn("curated exoplanet data", response["summary"])

    def test_ask_nasahub_returns_grounded_answer(self):
        rows = [
            {
                "neo_reference_id": "3542519",
                "name": "(2010 PK9)",
                "nasa_jpl_url": None,
                "absolute_magnitude_h": 20.5,
                "is_potentially_hazardous_asteroid": True,
                "is_sentry_object": False,
                "estimated_diameter_min_km": 0.21,
                "estimated_diameter_max_km": 0.47,
                "first_close_approach_date": None,
                "most_recent_close_approach_date": None,
                "approach_count": 0,
                "min_miss_distance_km": None,
                "max_velocity_kph": None,
                "latest_orbiting_body": None,
                "last_ingested_at": datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows)

        with patch("api.routes.analytics.call_openai_grounded_answer", return_value="Grounded answer") as mocked_call:
            response = ask_nasahub(
                payload=AskNasaHubRequest(
                    source="neows",
                    entity_id="3542519",
                    question="Explain this object",
                    include_live_enrichment=False,
                    history=[{"role": "user", "content": "What is this object?"}],
                ),
                db=db,
            )

        mocked_call.assert_called_once()
        self.assertEqual(
            mocked_call.call_args.kwargs["chat_history"],
            [{"role": "user", "content": "What is this object?"}],
        )
        self.assertEqual(response["answer"], "Grounded answer")
        self.assertEqual(response["source"], "neows")
        self.assertEqual(response["grounded_sources"], ["nasahub_local"])
        self.assertEqual(response["conversation"][-2]["role"], "user")
        self.assertEqual(response["conversation"][-2]["content"], "Explain this object")
        self.assertEqual(response["conversation"][-1]["role"], "assistant")
        self.assertEqual(response["conversation"][-1]["content"], "Grounded answer")
        self.assertEqual(response["citations"][0]["source"], "nasahub_local")
        self.assertEqual(response["citations"][0]["path"], "/analytics/neows/object/3542519")

    def test_ask_nasahub_includes_live_citation_when_available(self):
        rows = [
            {
                "neo_reference_id": "3542519",
                "name": "(2010 PK9)",
                "nasa_jpl_url": None,
                "absolute_magnitude_h": 20.5,
                "is_potentially_hazardous_asteroid": True,
                "is_sentry_object": False,
                "estimated_diameter_min_km": 0.21,
                "estimated_diameter_max_km": 0.47,
                "first_close_approach_date": None,
                "most_recent_close_approach_date": None,
                "approach_count": 0,
                "min_miss_distance_km": None,
                "max_velocity_kph": None,
                "latest_orbiting_body": None,
                "last_ingested_at": datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows)

        with (
            patch("api.routes.analytics.call_openai_grounded_answer", return_value="Grounded answer"),
            patch(
                "api.routes.analytics.fetch_neows_live_enrichment_payload",
                return_value={"source_url": "https://api.nasa.gov/neo/rest/v1/neo/3542519"},
            ),
        ):
            response = ask_nasahub(
                payload=AskNasaHubRequest(
                    source="neows",
                    entity_id="3542519",
                    question="Compare local vs live",
                    include_live_enrichment=True,
                ),
                db=db,
            )

        self.assertEqual(response["grounded_sources"], ["nasahub_local", "nasa_neows_live"])
        self.assertEqual(response["citations"][-1]["source"], "nasa_neows_live")

    def test_ask_nasahub_general_mode_uses_general_context(self):
        db = FakeSession()

        with (
            patch(
                "api.routes.analytics.build_general_context",
                return_value=(
                    "neows",
                    {"largest_objects": [{"entity_id": "3542519", "title": "(2010 PK9)"}]},
                    ["nasahub_local"],
                    [
                        {
                            "source": "nasahub_local",
                            "title": "NASAHub NeoWs general rankings",
                            "entity_id": None,
                            "path": "/analytics/neows/kpis",
                            "source_url": None,
                            "note": "general retrieval",
                        }
                    ],
                    [
                        {
                            "source": "neows",
                            "entity_id": "3542519",
                            "title": "(2010 PK9)",
                            "path": "/analytics/neows/object/3542519",
                            "note": "match",
                        }
                    ],
                ),
            ),
            patch("api.routes.analytics.call_openai_grounded_answer", return_value="General grounded answer") as mocked_call,
        ):
            response = ask_nasahub(
                payload=AskNasaHubRequest(
                    mode="general",
                    source="general",
                    question="Which is the biggest object that got close to Earth?",
                    include_live_enrichment=True,
                ),
                db=db,
            )

        mocked_call.assert_called_once()
        self.assertEqual(mocked_call.call_args.kwargs["source"], "neows")
        self.assertEqual(response["mode"], "general")
        self.assertEqual(response["source"], "neows")
        self.assertIsNone(response["entity_id"])
        self.assertEqual(response["answer"], "General grounded answer")
        self.assertEqual(response["matched_entities"][0]["entity_id"], "3542519")
        self.assertEqual(response["citations"][0]["path"], "/analytics/neows/kpis")

    def test_ask_nasahub_entity_mode_requires_entity(self):
        db = FakeSession()

        with self.assertRaises(HTTPException) as exc_info:
            ask_nasahub(
                payload=AskNasaHubRequest(
                    mode="entity",
                    source="neows",
                    entity_id=None,
                    question="Explain this object",
                ),
                db=db,
            )
        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertEqual(exc_info.exception.detail, "Entity mode requires entity_id")

    def test_list_osdr_dataset_summary_returns_rows_from_view(self):
        rows = [
            {
                "dataset_accession": "OSD-366",
                "dataset_label": "OSD-366",
                "title": None,
                "description": None,
                "data_source": None,
                "organism": None,
                "release_date": None,
                "repository_url": None,
                "assay_count": 12,
                "sample_count": 6522,
                "file_count": 12736,
                "last_ingested_at": datetime(2026, 4, 3, 18, 0, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows)

        response = list_osdr_dataset_summary(db=db)

        self.assertEqual(response, rows)
        self.assertIn("FROM dmt_generic.v_dmt_osdr_dataset_summary", db.queries[0])

    def test_list_osdr_assay_type_summary_returns_rows_from_view(self):
        rows = [
            {
                "assay_type": "Unknown",
                "assay_count": 842,
                "distinct_dataset_count": 628,
                "distinct_technology_count": 1,
                "distinct_platform_count": 1,
            }
        ]
        db = FakeSession(rows=rows)

        response = list_osdr_assay_type_summary(db=db)

        self.assertEqual(response, rows)
        self.assertIn("FROM dmt_generic.v_dmt_osdr_assay_type_summary", db.queries[0])

    def test_list_osdr_datasets_returns_paginated_rows_with_filters(self):
        rows = [
            {
                "dataset_accession": "OSD-366",
                "dataset_label": "OSD-366",
                "title": None,
                "description": None,
                "data_source": None,
                "organism": None,
                "release_date": None,
                "repository_url": None,
                "last_ingested_at": datetime(2026, 4, 3, 18, 0, tzinfo=timezone.utc),
            }
        ]
        db = FakeSession(rows=rows, scalar_values=[1])

        response = list_osdr_datasets(
            limit=5,
            offset=10,
            data_source=None,
            dataset_accession="OSD-366",
            db=db,
        )

        self.assertEqual(
            response,
            {
                "items": rows,
                "total": 1,
                "limit": 5,
                "offset": 10,
            },
        )
        self.assertIn("FROM dmt_generic.v_dmt_osdr_dataset_catalog c", db.queries[1])
        self.assertIn("c.dataset_accession = CAST(:dataset_accession AS text)", db.queries[0])
        self.assertEqual(
            db.params[0],
            {
                "limit": 5,
                "offset": 10,
                "data_source": None,
                "dataset_accession": "OSD-366",
            },
        )


if __name__ == "__main__":
    unittest.main()
