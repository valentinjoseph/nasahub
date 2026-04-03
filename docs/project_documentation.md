NasaHub is a self-hosted NASA data platform running on a Lenovo M920q.

## Project goal

The platform is designed to:

* ingest space/science data APIs into PostgreSQL
* keep a raw staging layer close to source payloads
* track ingestion runs and row lineage centrally
* expose data through a FastAPI backend
* later support views, monitoring, analytics, and application features on top of the staged data

## Machine roles

### Lenovo M920q

Always-on server:

* Ubuntu Server 24.04
* Docker host
* PostgreSQL in Docker
* FastAPI in Docker
* ingestion jobs
* cron scheduling
* observability/admin stack

### MacBook Air

Admin/dev machine only:

* SSH into Lenovo
* VS Code Remote SSH
* DBeaver through SSH tunnel
* browser access to LAN-exposed services

There is no Raspberry Pi in the setup anymore.

## Operating model

* all project code lives on the Lenovo
* development is done remotely from the Mac via Remote SSH
* Docker runs on the Lenovo
* PostgreSQL runs in Docker on the Lenovo
* FastAPI runs in Docker on the Lenovo
* ingestion jobs run on the Lenovo
* the Mac is only the admin/development client

## Repository structure

* `api/` → FastAPI app + Dockerfile
* `core/` → shared config
* `db/` → DB session/deps/Alembic
* `ingestors/` → source-specific loaders
* `infra/` → docker-compose + `.env`
* `scripts/` → cron wrapper scripts
* `logs/` existed initially but should now be ignored and no longer used for ingestion output

## Database design

### Design principles

* raw staging first
* source payloads kept close to source
* lineage tracked centrally
* cleaned/latest/business logic deferred to downstream views/models later

### Technical schemas/tables

Schemas:

* `tech`
* `stg_eonet`
* `stg_neows`
* `stg_exoplanet`
* `stg_osdr`

Technical tables:

* `tech.run_management`

  * one row per ingestion run
  * tracks source, endpoint, status, timing, inserted row count
* `tech.id_management`

  * one row per inserted staging row
  * tracks lineage between source record, staging row, and run

### Staging metadata convention

All staging tables use:

* `id`
* `s_ingested_at`
* `s_source_url`
* `s_run_id`
* `s_payload`

## What has been loaded into PostgreSQL

### 1. EONET

Loaded into `stg_eonet`:

* `events`
* `categories`
* `sources`
* `layers`

Current dedupe:

* `events` → `event_id`
* `categories` → `category_id`
* `sources` → `source_id`
* `layers` → `(category_id, layer_name)`

### 2. NeoWs

Loaded into `stg_neows`:

* `neo_feed`
* `neo_browse`
* `neo_lookup` table exists, but operationally it is not essential and is not the main recurring source

Current dedupe:

* `neo_feed` → `(neo_reference_id, close_approach_date, orbiting_body)`
* `neo_lookup` → `neo_reference_id`
* `neo_browse` → `neo_reference_id`

Notes:

* `neo_feed` is the main recurring operational load
* `neo_browse` was used as a large catalog backfill/reference load
* `neo_browse` was made more robust with per-page commits, retry logic, and fallback handling for missing names

### 3. Exoplanet Archive

Loaded into `stg_exoplanet`:

* `ps`
* `pscomppars`

Current dedupe:

* `ps` → `pl_name`
* `pscomppars` → `pl_name`

Operational choice:

* `pscomppars` is the main scheduled table
* `ps` is kept as a lower-frequency reference refresh

### 4. OSDR

Loaded into `stg_osdr`:

* `datasets`
* `assays`
* `samples`
* `files`

Current dedupe:

* `datasets` → `dataset_accession`
* `assays` → `assay_accession`
* `samples` → `sample_accession`
* `files` → `file_accession`

Notes:

* OSDR required iterative correction because payload shapes were hierarchical and inconsistent across endpoints
* final working load order is:

  1. datasets
  2. assays
  3. samples
  4. files

## APIs used and what each does

### EONET

Purpose:

* Earth Observatory Natural Event Tracker
* provides natural event data and reference metadata

Used endpoints/data:

* events → natural events feed
* categories → event categories metadata
* sources → source system metadata
* layers → map/layer metadata associated with categories

Operational use:

* lightweight daily refreshes
* small enough that simple full pulls with dedupe are acceptable

### NeoWs

Purpose:

* Near Earth Object Web Service
* asteroid / NEO information from NASA

Used endpoints/data:

* `neo_feed`

  * date-window feed of near-Earth objects and close approaches
  * good for recurring operational ingestion
* `neo_browse`

  * broad paginated catalog of NEOs
  * good for baseline backfill/reference loading
* `neo_lookup`

  * single-object lookup by asteroid ID
  * implemented structurally but not central to recurring ingestion

Operational use:

* `neo_feed` scheduled daily
* `neo_browse` treated as backfill/occasional refresh, not routine daily ingestion

### Exoplanet Archive

Purpose:

* NASA Exoplanet Archive
* structured catalog of exoplanet and host system information

Used tables via API/TAP:

* `ps`

  * planetary systems table
* `pscomppars`

  * composite planetary parameters table, operationally the most useful one-row-per-planet style table

Operational use:

* `pscomppars` scheduled weekly
* `ps` scheduled monthly

### OSDR

Purpose:

* Open Science Data Repository
* life sciences / biological & physical sciences metadata and associated files

Loaded hierarchy:

* datasets
* assays
* samples
* files

Operational use:

* `datasets` and `files` scheduled weekly
* `assays` and `samples` scheduled monthly

## Ingestor architecture pattern

Each loader follows the same core pattern:

* call source API
* create a row in `tech.run_management`
* insert new rows into staging
* insert lineage rows into `tech.id_management`
* mark the run as success or failure

Deduplication is done in staging using:

* business-key unique constraints
* `ON CONFLICT DO NOTHING RETURNING id`

## FastAPI

FastAPI container is running.

Current endpoint implemented:

* `/health`

FastAPI exists mainly as the application/backend layer to expose staged or curated data later.

## Scheduling / cron

### Current schedule

#### Daily

* 08:00 `eonet_events`
* 08:05 `eonet_categories`
* 08:10 `eonet_sources`
* 08:15 `eonet_layers`
* 08:20 `neows_feed`

#### Weekly, every Monday

* 08:30 `exoplanet_pscomppars`
* 09:00 `osdr_datasets`
* 09:10 `osdr_files`

#### Monthly, on the 1st

* 08:45 `exoplanet_ps`
* 09:20 `osdr_assays`
* 09:30 `osdr_samples`

### Scheduling model

* one wrapper script per ingestion job under `scripts/`
* dedicated cron files under `/etc/cron.d/`
* newer jobs are silent with `> /dev/null 2>&1`
* logging is meant to rely on PostgreSQL technical tables, not flat log files

## Important logging change

Originally, project ingestion logs were being written to files under `logs/`, and one of them exceeded GitHub’s 100 MB file limit.

Decision taken:

* stop creating ingestion log files
* no more project log append behavior in wrappers
* rely on `tech.run_management` and `tech.id_management` for monitoring/auditing
* `logs/` and `*.log` are ignored in git

## Git issue resolved

Problem:

* committed logs blocked push because one exceeded GitHub’s file size limit

Fix applied:

* `logs/` and `*.log` added to `.gitignore`
* git history rewritten with `git filter-repo --force --path logs/ --invert-paths`
* remote may need re-adding after rewrite
* push requires force push afterward

## Security hardening completed

### SSH

Configured securely:

* `PasswordAuthentication no`
* `PermitRootLogin no`
* `PubkeyAuthentication yes`

### Firewall / UFW

UFW was hardened.

Inbound SSH is only allowed from:

* the user’s public IP
* the Mac’s LAN IP: `192.168.1.14`

Current UFW posture is intentionally minimal.

### Docker / network exposure

Originally, many services were published too broadly on `0.0.0.0`.

That was hardened.

Current exposure model:

* PostgreSQL → bound to `127.0.0.1:5432`
* FastAPI → intended to remain private unless LAN browser access is explicitly needed later
* observability/admin services → bound to Lenovo LAN IP `192.168.1.28`
* Homepage → bound to `192.168.1.28:3005`

### Practical result

* services are reachable on home Wi-Fi / home LAN
* services are not reachable from the public internet
* PostgreSQL is not exposed to LAN or internet
* SSH is restricted
* Homepage is LAN-only

### DBeaver / PostgreSQL access

Because PostgreSQL is localhost-bound:

* direct LAN DB access no longer works
* DBeaver must connect via SSH tunnel

DBeaver pattern:

* DB host: `127.0.0.1`
* SSH host: Lenovo LAN IP
* SSH auth: Mac private key, typically `/Users/valentinjoseph/.ssh/id_ed25519`

### Homepage / observability

Homepage links must use LAN URLs, not Docker service names, for browser clickability.

Examples used:

* Grafana → `http://192.168.1.28:3000`
* Uptime Kuma → `http://192.168.1.28:3001`
* Dozzle → `http://192.168.1.28:8080`
* Prometheus → `http://192.168.1.28:9090`
* Portainer → `https://192.168.1.28:9443`

The obsolete `Pi SSH` entry should be removed.

### Additional security notes

* Grafana admin password was exposed in chat and should be rotated
* router should have:

  * no port forwarding to Lenovo
  * no DMZ to Lenovo
  * ideally UPnP disabled

## Main operational conclusions

* EONET is fully implemented and scheduled daily
* NeoWs is implemented, with `neo_feed` as the recurring loader and `neo_browse` as backfill/reference
* Exoplanet is implemented and scheduled at mixed weekly/monthly cadence
* OSDR is implemented and scheduled at mixed weekly/monthly cadence
* the ingestion framework pattern is now established across multiple APIs
* PostgreSQL staging + technical lineage is the core monitoring/audit layer
* file-based ingestion logs have been intentionally retired
* the stack is hardened and LAN-only for admin/observability access

## Good next step after this summary

Likely next source:

* CelesTrak / TLE-related ingestion

Candidate staging schema already discussed:

* `stg_celestrak`

Candidate first tables discussed:

* `gp_active`
* `satcat_active`

This would extend the platform from NASA APIs into orbital tracking/catalog data.
