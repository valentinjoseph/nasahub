from pathlib import Path
from datetime import date, datetime, timezone
import unittest
from unittest.mock import patch

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
from api.routes.analytics import (
    ANALYTICS_ENDPOINTS,
    get_analytics_catalog,
    list_eonet_category_summary,
    list_eonet_event_overview,
    list_exoplanet_catalog,
    list_exoplanet_discovery_method_summary,
    list_exoplanet_discovery_yearly_summary,
    list_ingestion_status,
    list_neows_daily_summary,
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
                "/analytics/eonet/category-summary",
                "/analytics/eonet/event-overview",
                "/analytics/exoplanet/discovery-yearly-summary",
                "/analytics/exoplanet/discovery-method-summary",
                "/analytics/exoplanet/catalog",
                "/analytics/osdr/dataset-summary",
                "/analytics/osdr/assay-type-summary",
                "/analytics/osdr/datasets",
            },
        )
        ingestion_status = openapi["paths"]["/analytics/ingestion-status"]["get"]
        analytics_catalog = openapi["paths"]["/analytics/catalog"]["get"]
        daily_summary = openapi["paths"]["/analytics/neows/daily-summary"]["get"]
        kpis = openapi["paths"]["/analytics/neows/kpis"]["get"]
        eonet_category_summary = openapi["paths"]["/analytics/eonet/category-summary"]["get"]
        eonet_event_overview = openapi["paths"]["/analytics/eonet/event-overview"]["get"]
        exoplanet_yearly = openapi["paths"]["/analytics/exoplanet/discovery-yearly-summary"]["get"]
        exoplanet_method = openapi["paths"]["/analytics/exoplanet/discovery-method-summary"]["get"]
        exoplanet_catalog = openapi["paths"]["/analytics/exoplanet/catalog"]["get"]
        osdr_dataset_summary = openapi["paths"]["/analytics/osdr/dataset-summary"]["get"]
        osdr_assay_type_summary = openapi["paths"]["/analytics/osdr/assay-type-summary"]["get"]
        osdr_datasets = openapi["paths"]["/analytics/osdr/datasets"]["get"]

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
