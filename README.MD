# NASAHub

Self-hosted NASA data platform running on the **Lenovo M920q**.

NASAHub ingests raw source data into PostgreSQL, curates analytics-ready views, exposes them through FastAPI, and now includes a private dashboard for admin use from the MacBook.

Source APIs and datasets currently in scope include:

* EONET
* NeoWs
* Exoplanet Archive
* OSDR

## Goal

NASAHub is being built as a private, self-hosted analytics platform that can later support:

* curated analytics endpoints
* dashboards and internal tools
* downstream apps
* a future chat or agent layer on top of trusted curated data

The core design principle is:

* ingest raw source data into staging
* track lineage and run status centrally
* build curated views above staging
* expose curated data through a stable API instead of direct database access

## Machines And Roles

### Lenovo M920q

The Lenovo is the real NASAHub server. It hosts:

* Ubuntu Server 24.04
* Docker
* PostgreSQL
* FastAPI
* Alembic migrations
* ingestion jobs and cron wrappers
* the project codebase
* the stored data

### MacBook Air

The MacBook is the admin and development machine. It is used to:

* connect to the Lenovo with SSH
* edit the code with VS Code Remote SSH
* inspect PostgreSQL through an SSH tunnel
* browse the private dashboard and API

Important operating model:

* all code lives on the Lenovo
* all data lives on the Lenovo
* Docker runs on the Lenovo
* PostgreSQL runs on the Lenovo
* FastAPI runs on the Lenovo
* the MacBook is only the remote admin/dev client

## Current Architecture

NASAHub now has four practical layers:

1. Ingestion layer
   Source-specific ingestors load raw data into PostgreSQL staging schemas.
2. Technical metadata layer
   `tech.run_management` and `tech.id_management` track run status, inserted rows, and lineage.
3. Curated analytics layer
   `dmt_generic` contains analytics-ready views built on top of staging.
4. Access layer
   FastAPI exposes curated analytics endpoints, and a private dashboard consumes those endpoints.

### Architecture Diagram

![NASAHub architecture illustration](docs/assets/nasahub-architecture.png)

```mermaid
flowchart LR
    M[MacBook Air\nAdmin, VS Code Remote SSH, Browser]
    L[Lenovo M920q\nUbuntu Server 24.04]
    F[FastAPI in Docker\n/analytics, /dashboard, /health, /analytics/ask]
    P[PostgreSQL in Docker]
    T[tech schema\nrun_management\nid_management]
    S[staging schemas\nstg_eonet\nstg_neows\nstg_exoplanet\nstg_osdr]
    D[dmt_generic\ncurated analytics views]
    UI[Private Dashboard]
    A[Ask NASAHub\nentity mode\ngeneral mode]
    N[Live NASA NeoWs enrichment]
    O[OpenAI grounded answers]

    M -->|SSH, browser| L
    L --> F
    L --> P
    P --> T
    P --> S
    S --> D
    T --> D
    D --> F
    F --> UI
    F --> A
    A --> D
    A --> N
    A --> O
```

### Runtime Flow

1. Cron wrappers on the Lenovo trigger source ingestors.
2. Ingestors load raw source-shaped data into PostgreSQL staging schemas.
3. `tech.*` tables record run status, inserted rows, and lineage.
4. `dmt_generic` views reshape raw data into analytics-ready datasets.
5. FastAPI exposes stable routes for analytics, detail views, and Ask NASAHub retrieval.
6. The private dashboard uses those endpoints for overview, exploration, and chat-style retrieval.
7. Ask NASAHub answers from curated NASAHub data first, then optionally enriches with live NASA and OpenAI-backed grounded generation.

## Repository Structure

```text
nasahub/
├── api/
│   ├── main.py
│   ├── routes/
│   │   └── analytics.py
│   └── schemas.py
├── core/
│   └── config.py
├── db/
│   ├── deps.py
│   ├── session.py
│   └── alembic/versions/
├── docs/
│   └── project_documentation.md
├── frontend/
│   ├── index.html
│   ├── dashboard.css
│   └── dashboard.js
├── ingestors/
├── infra/
│   └── docker-compose.yml
├── scripts/
└── tests/
    └── test_analytics_routes.py
```

## Database Design

### Schemas In Use

* `tech`
* `stg_eonet`
* `stg_neows`
* `stg_exoplanet`
* `stg_osdr`
* `dmt_generic`

### Technical Tables

#### `tech.run_management`

Tracks one row per ingestion execution, including:

* `source_name`
* `source_endpoint`
* `status`
* `run_started_at`
* `run_finished_at`
* `records_inserted`

#### `tech.id_management`

Tracks lineage between source records, staging rows, and runs.

### Staging Convention

Staging tables keep source data close to the original payload and include:

* `id`
* `s_ingested_at`
* `s_source_url`
* `s_run_id`
* `s_payload`

### Curated Analytics Schema

`dmt_generic` contains the curated analytics views used by the API and dashboard.

Current curated views include:

* `v_dmt_ingestion_status`
* `v_dmt_neows_daily_summary`
* `v_dmt_neows_kpis`
* `v_dmt_eonet_category_summary`
* `v_dmt_eonet_event_overview`
* `v_dmt_exoplanet_discovery_yearly_summary`
* `v_dmt_exoplanet_discovery_method_summary`
* `v_dmt_exoplanet_catalog`
* `v_dmt_osdr_dataset_summary`
* `v_dmt_osdr_assay_type_summary`
* `v_dmt_osdr_dataset_catalog`

## FastAPI

FastAPI runs in Docker on the Lenovo and acts as the controlled access layer over curated data.

### Health And Platform Endpoints

* `GET /health/live`
* `GET /health/ready`
* `GET /health`
* `GET /ingestion-runs`
* `GET /analytics/catalog`

### Analytics Endpoints

#### Tech / platform

* `GET /analytics/ingestion-status`

#### NeoWs

* `GET /analytics/neows/daily-summary`
* `GET /analytics/neows/kpis`

#### EONET

* `GET /analytics/eonet/category-summary`
* `GET /analytics/eonet/event-overview`

Supported query parameters:

* `limit`
* `offset`
* `category_id`
* `event_status`

#### Exoplanet

* `GET /analytics/exoplanet/discovery-yearly-summary`
* `GET /analytics/exoplanet/discovery-method-summary`
* `GET /analytics/exoplanet/catalog`

Supported query parameters:

* `limit`
* `offset`
* `discovery_method`
* `disc_year`

#### OSDR

* `GET /analytics/osdr/dataset-summary`
* `GET /analytics/osdr/assay-type-summary`
* `GET /analytics/osdr/datasets`

Supported query parameters:

* `limit`
* `offset`
* `data_source`
* `dataset_accession`

### API Contract Features

The analytics API now includes:

* typed response models
* pagination wrappers for larger result sets
* endpoint discovery through `/analytics/catalog`
* liveness and readiness endpoints
* optional private token-based auth
* request IDs and structured access logging

## Private Dashboard

NASAHub now includes a private dashboard served directly by FastAPI.

Routes:

* `GET /dashboard`
* `GET /` redirects to `/dashboard`

Static assets:

* `/dashboard-assets/dashboard.css`
* `/dashboard-assets/dashboard.js`

The dashboard is intentionally lightweight:

* static HTML/CSS/JS
* no Node or frontend build system
* designed for private use from the MacBook browser

Dashboard coverage:

* system overview
* ingestion status
* NeoWs signals
* EONET activity
* Exoplanet discovery
* OSDR operations
* filtered explorer panels for large paginated endpoints

## Security And Exposure Model

Current posture:

* PostgreSQL remains private on the Lenovo
* users should consume data through the API, not direct DB access
* the dashboard is intended as a private admin interface
* API auth can be enabled with environment variables

Relevant config in `core/config.py`:

* `API_ENABLE_DOCS`
* `API_REQUIRE_AUTH`
* `API_AUTH_TOKEN`
* `API_TITLE`
* `API_VERSION`

If auth is enabled, protected routes accept either:

* `X-API-Key: <token>`
* `Authorization: Bearer <token>`

Health endpoints and the dashboard remain usable according to the configured auth exemptions in the app.

## Scheduling And Monitoring

Ingestion jobs are triggered by wrapper scripts under `scripts/`.

Monitoring no longer relies on flat log files. The intended monitoring model is:

* `tech.run_management` for run health and timing
* `tech.id_management` for lineage
* curated analytics views such as ingestion status
* API health/readiness endpoints
* structured container logs for request tracing

## Testing

Current API and analytics coverage is backed by:

* `tests/test_analytics_routes.py`

The tests cover:

* route registration in OpenAPI
* response model wiring
* pagination/filter behavior
* analytics catalog behavior
* auth helper behavior
* health endpoint behavior
* request ID and access-log helpers
* dashboard file presence
* view-backed route query behavior

Run tests locally on the Lenovo:

```bash
./.venv/bin/python -m unittest tests.test_analytics_routes
```

## How To Run

From the Lenovo project directory:

```bash
cd /home/hl-lenovo/projects/nasahub/infra
docker compose up -d --build
```

Useful URLs:

* API docs: `http://192.168.1.28:8000/docs` when docs are enabled
* Dashboard: `http://192.168.1.28:8000/dashboard`
* Health: `http://192.168.1.28:8000/health/ready`

## Current Status

Implemented and live:

* raw staging schemas for EONET, NeoWs, Exoplanet, and OSDR
* technical lineage and run-management tables
* curated analytics views in `dmt_generic`
* analytics API endpoints across all current sources
* typed response models
* pagination and filtering for larger endpoints
* analytics endpoint catalog
* request tracing and structured access logs
* optional API auth layer
* private dashboard served from FastAPI
* Ask NASAHub with entity mode and general retrieval mode
* intent-aware broad-question ranking across NeoWs, EONET, and Exoplanet
* test coverage for analytics routing and helpers

## Next Likely Steps

Recommended next areas after documentation:

* dashboard polish and richer per-source exploration
* stronger auth and access control if exposure broadens
* additional curated views for new domains
* frontend UX improvements once API contracts are stable
* future GenAI/chat layer on top of curated analytics
