# NasaHub
source: https://api.nasa.gov/
## Goal

NasaHub is a self-hosted NASA data ingestion project running on the **Lenovo M920q**.

The goal is to:

* ingest NASA API data into PostgreSQL
* keep a raw **staging layer** close to source payloads
* track ingestion runs and row lineage
* expose data through an API
* later build monitoring, views, and app features on top

Current first scope:

* **EONET**

  * events
  * categories
  * sources
  * layers

Planned next scope:

* **NeoWs**

  * neo_feed
  * neo_lookup
  * neo_browse

* **Open Science Data Repository**

* **TLE API**

* **Exoplanet**
---

## Machines and roles

### Lenovo M920q

Main always-on server.

Responsibilities:

* Ubuntu Server 24.04
* Docker host
* PostgreSQL
* FastAPI container
* ingestion jobs
* cron scheduling
* logs
* observability stack already running

### MacBook Air

Admin and development machine.

Responsibilities:

* SSH into Lenovo
* VS Code Remote SSH
* DBeaver connection to PostgreSQL
* browser access to app and dashboards
* optional remote Docker control

There is **no Raspberry Pi** in the setup anymore.

---

## Operating model

Development happens from the Mac, but code lives on Lenovo.

Pattern:

* edit code from Mac in VS Code via Remote SSH
* files are stored on Lenovo
* Docker runs on Lenovo
* PostgreSQL runs in Docker on Lenovo
* FastAPI runs in Docker on Lenovo
* ingestion jobs run on Lenovo
* Mac is only the admin/dev client

---

## Project architecture

### Repository structure

```text
nasahub/
├── api/
│   ├── __init__.py
│   ├── main.py
│   └── Dockerfile
├── core/
│   ├── __init__.py
│   └── config.py
├── db/
│   ├── __init__.py
│   ├── deps.py
│   ├── session.py
│   └── alembic/
├── ingestors/
│   ├── __init__.py
│   └── eonet/
│       ├── __init__.py
│       ├── events.py
│       ├── categories.py
│       ├── sources.py
│       └── layers.py
├── infra/
│   ├── docker-compose.yml
│   └── .env
├── logs/
├── scripts/
└── requirements.txt
```

---

## Current technical design

## 1. Infrastructure

Docker Compose currently manages:

* `postgres`
* `api`
* `ingestor` service definition for one-shot jobs

### Containers

* `nasahub-postgres`: always on
* `nasahub-api`: always on
* `ingestor`: run on demand from cron

### API

FastAPI runs in Docker with Uvicorn inside the container.

That means:

* no need for a shell session
* no need for the Mac to stay on
* Lenovo keeps the API running on its own

---

## 2. Configuration

Shared configuration is centralized in:

```text
core/config.py
```

It reads environment variables from:

```text
infra/.env
```

Typical variables:

* `POSTGRES_DB`
* `POSTGRES_USER`
* `POSTGRES_PASSWORD`
* `POSTGRES_HOST`
* `POSTGRES_PORT`

---

## 3. Database design

### Main design principle

The current database approach is:

* **raw staging first**
* keep source data close to API payloads
* add ingestion metadata columns
* add technical lineage tables
* build cleaned views or downstream models later

---

## Schemas

### `tech`

Technical metadata and lineage.

### `stg_eonet`

Raw staging tables for EONET.

### `stg_neows`

Reserved for upcoming NeoWs ingestion.

---

## Tech schema

### `tech.run_management`

Tracks each ingestion run.

Purpose:

* one row per execution
* stores run metadata and status

Current fields:

* `s_run_id`
* `source_name`
* `source_endpoint`
* `status`
* `run_started_at`
* `run_finished_at`
* `records_inserted`
* `created_at`

Meaning:

* `source_name`: API family, for example `eonet`
* `source_endpoint`: endpoint name, for example `events`
* `status`: current run state
* `records_inserted`: number of newly inserted rows

---

### `tech.id_management`

Tracks lineage for inserted staging rows.

Purpose:

* one row per inserted staging record
* stores which staging row was created
* links staging insert to run metadata

Current fields:

* `id`
* `source_name`
* `source_table`
* `source_record_id`
* `staging_schema`
* `staging_row_id`
* `s_run_id`
* `s_source_url`
* `s_ingested_at`

Meaning:

* `source_record_id`: identifier from the source API
* `staging_schema`: schema where the row was inserted
* `staging_row_id`: actual surrogate id of the inserted staging row
* `s_run_id`: ingestion run that created the row

---

## Staging metadata convention

Every staging table includes technical columns:

* `id`
* `s_ingested_at`
* `s_source_url`
* `s_run_id`
* `s_payload`

Purpose:

* `id`: local surrogate key
* `s_ingested_at`: timestamp of ingestion
* `s_source_url`: exact API endpoint used
* `s_run_id`: link to `tech.run_management`
* `s_payload`: raw source JSON payload

---

## EONET staging tables

### `stg_eonet.events`

Stores event records from EONET events endpoint.

Main source fields:

* `event_id`
* `title`
* `description`
* `link`
* `closed`
* `categories`
* `sources`
* `geometry`

Notes:

* nested structures are stored as JSONB
* duplicates are prevented on `event_id`

---

### `stg_eonet.categories`

Stores EONET categories.

Main source fields:

* `category_id`
* `title`
* `description`
* `link`
* `layers`

Notes:

* `layers` is stored as text URL
* duplicates are prevented on `category_id`

---

### `stg_eonet.sources`

Stores EONET sources.

Main source fields:

* `source_id`
* `title`
* `source`
* `link`

Notes:

* duplicates are prevented on `source_id`

---

### `stg_eonet.layers`

Stores one row per actual layer entry returned from category-specific layers endpoints.

Main fields:

* `category_id`
* `category_title`
* `layer_name`
* `service_url`
* `service_type_id`
* `parameters`
* `endpoint_link`
* `response_title`
* `response_description`

Notes:

* layers are fetched from category `layers` URLs
* duplicates are prevented on `(category_id, layer_name)`

---

## Deduplication strategy

The project currently uses **business-key deduplication** in staging.

Meaning:

* same source record should not be inserted twice
* repeated hourly runs skip existing rows

Current dedupe keys:

* events → `event_id`
* categories → `category_id`
* sources → `source_id`
* layers → `(category_id, layer_name)`

Loaders use:

* `ON CONFLICT DO NOTHING RETURNING id`

Behavior:

* if the row is new, it is inserted and tracked in `tech.id_management`
* if it already exists, it is skipped

---

## Ingestor architecture

### Current EONET ingestors

Implemented:

* `ingestors.eonet.events`
* `ingestors.eonet.categories`
* `ingestors.eonet.sources`
* `ingestors.eonet.layers`

### Loader pattern

Each loader does:

1. call the source API
2. insert a row in `tech.run_management`
3. insert new rows into staging
4. insert lineage rows into `tech.id_management`
5. update run status to `success`

---

## API

FastAPI is available through the Dockerized API service.

Current endpoint:

* `/health`

The health endpoint checks:

* API is up
* database connection works

---

## Scheduling

### Current approach

Hourly ingestion is scheduled on the Lenovo via **cron**.

Cron runs one-shot Docker ingestor jobs.

Pattern:

* start container
* run one ingestion module
* write output to log file
* container exits

### Current schedule

EONET jobs are staggered across the hour:

* events
* categories
* sources
* layers

This avoids all jobs running at the exact same minute.

---

## Logging

Cron redirects stdout and stderr into project log files under:

```text
/home/hl-lenovo/projects/nasahub/logs/
```

One log file per ingestion type, not one file per execution.

Examples:

* `eonet_events.log`
* `eonet_categories.log`
* `eonet_sources.log`
* `eonet_layers.log`

### Rotation

Log rotation is handled by system `logrotate`, using a custom config under:

```text
/etc/logrotate.d/nasahub
```

So logs rotate automatically on Lenovo without needing custom cron entries for rotation.

---

## Current status

Working:

* PostgreSQL in Docker
* FastAPI in Docker
* Alembic migrations
* EONET staging schema
* EONET technical lineage schema
* EONET ingestors
* hourly scheduling on Lenovo
* file logging with rotation

Not done yet:

* NeoWs staging tables
* NeoWs ingestors
* richer API endpoints
* frontend
* analytical views
* dashboards specific to project data

---

## Next planned steps

Recommended order:

1. let hourly EONET schedule run and verify behavior
2. review logs and run counts
3. confirm no duplicate inserts occur
4. add `stg_neows` tables
5. implement NeoWs loaders:

   * `neo_feed`
   * `neo_lookup`
   * `neo_browse`
6. expose read endpoints in FastAPI
7. later add frontend or Grafana views

---

## Core principles for the repository

This project should continue following these rules:

* code lives on Lenovo
* Mac is only admin/dev machine
* app services run in Docker on Lenovo
* raw source data first
* staging schema stays close to source API
* technical lineage is tracked centrally
* dedupe happens in staging through business keys
* cleaned/latest-record logic belongs in views or downstream models, not in raw staging
