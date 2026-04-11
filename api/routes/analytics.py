import json

from fastapi import APIRouter, Depends, HTTPException, Query
import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.schemas import (
    AskNasaHubCitation,
    AskNasaHubMessage,
    AskNasaHubMatch,
    AskNasaHubRequest,
    AskNasaHubResponse,
    AnalyticsCatalogResponse,
    AnalyticsEndpointInfoResponse,
    EonetEventDetailResponse,
    EonetInsightResponse,
    EonetCategorySummaryResponse,
    EonetEventOverviewPageResponse,
    EonetEventOverviewResponse,
    ExoplanetCatalogPageResponse,
    ExoplanetDiscoveryMethodSummaryResponse,
    ExoplanetDiscoveryYearlySummaryResponse,
    ExoplanetInsightResponse,
    ExoplanetPlanetDetailResponse,
    ExoplanetPlanetSearchResultResponse,
    IngestionStatusResponse,
    NeoWsApproachPageResponse,
    NeoWsDailySummaryResponse,
    NeoWsInsightResponse,
    NeoWsLiveEnrichmentResponse,
    NeoWsObjectDetailResponse,
    NeoWsObjectSearchResultResponse,
    NeoWsKpiResponse,
    OsdrAssayTypeSummaryResponse,
    OsdrDatasetCatalogPageResponse,
    OsdrDatasetSummaryResponse,
)
from core.config import NASA_API_KEY, OPENAI_API_KEY, OPENAI_MODEL
from db.deps import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])

NEOWS_LOOKUP_URL = "https://api.nasa.gov/neo/rest/v1/neo"

ANALYTICS_ENDPOINTS = [
    AnalyticsEndpointInfoResponse(
        path="/analytics/ingestion-status",
        source="tech",
        summary="Latest ingestion status by source and endpoint.",
        paginated=False,
        filters=[],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/neows/daily-summary",
        source="neows",
        summary="Daily near-earth object rollups by close approach date.",
        paginated=False,
        filters=[],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/neows/kpis",
        source="neows",
        summary="Near-earth object key records such as biggest, fastest, and closest.",
        paginated=False,
        filters=[],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/neows/object/{neo_reference_id}",
        source="neows",
        summary="Object-level NeoWs profile for dashboard and agent retrieval.",
        paginated=False,
        filters=[],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/neows/objects",
        source="neows",
        summary="NeoWs object finder for searching by name or reference ID.",
        paginated=False,
        filters=["query", "limit"],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/neows/object/{neo_reference_id}/live-enrichment",
        source="neows",
        summary="Live NASA NeoWs enrichment for a specific object profile.",
        paginated=False,
        filters=[],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/neows/object/{neo_reference_id}/approaches",
        source="neows",
        summary="Paginated close-approach history for a specific NeoWs object.",
        paginated=True,
        filters=["limit", "offset"],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/neows/object/{neo_reference_id}/insight",
        source="neows",
        summary="Contextual NeoWs object insights for dashboard and agent usage.",
        paginated=False,
        filters=["mode"],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/eonet/event/{event_id}",
        source="eonet",
        summary="Event-level EONET detail for dashboard and agent retrieval.",
        paginated=False,
        filters=[],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/eonet/event/{event_id}/insight",
        source="eonet",
        summary="Contextual EONET event insights for dashboard and agent usage.",
        paginated=False,
        filters=["mode"],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/eonet/category-summary",
        source="eonet",
        summary="Event rollups by EONET category.",
        paginated=False,
        filters=[],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/eonet/event-overview",
        source="eonet",
        summary="Paginated EONET event overview with category and status filters.",
        paginated=True,
        filters=["category_id", "event_status", "limit", "offset"],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/exoplanet/discovery-yearly-summary",
        source="exoplanet",
        summary="Discovery counts by year with cumulative totals.",
        paginated=False,
        filters=[],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/exoplanet/discovery-method-summary",
        source="exoplanet",
        summary="Discovery counts grouped by discovery method.",
        paginated=False,
        filters=[],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/exoplanet/catalog",
        source="exoplanet",
        summary="Paginated exoplanet catalog with discovery method and year filters.",
        paginated=True,
        filters=["discovery_method", "disc_year", "limit", "offset"],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/exoplanet/planets",
        source="exoplanet",
        summary="Exoplanet finder for searching by planet or host name.",
        paginated=False,
        filters=["query", "limit"],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/exoplanet/planet/{pl_name}",
        source="exoplanet",
        summary="Planet-level exoplanet detail for dashboard and agent retrieval.",
        paginated=False,
        filters=[],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/exoplanet/planet/{pl_name}/insight",
        source="exoplanet",
        summary="Contextual exoplanet insights for dashboard and agent usage.",
        paginated=False,
        filters=["mode"],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/osdr/dataset-summary",
        source="osdr",
        summary="Dataset-level OSDR relationship counts for assays, samples, and files.",
        paginated=False,
        filters=[],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/osdr/assay-type-summary",
        source="osdr",
        summary="OSDR assay counts grouped by assay type.",
        paginated=False,
        filters=[],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/osdr/datasets",
        source="osdr",
        summary="Paginated OSDR dataset catalog with basic dataset filters.",
        paginated=True,
        filters=["data_source", "dataset_accession", "limit", "offset"],
    ),
    AnalyticsEndpointInfoResponse(
        path="/analytics/ask",
        source="assistant",
        summary="Top-level grounded Ask NASAHub route backed by curated retrieval and an LLM.",
        paginated=False,
        filters=[],
    ),
]


def fetch_view_rows(db: Session, query: str) -> list[dict]:
    result = db.execute(text(query))
    return [dict(row) for row in result.mappings().all()]


def fetch_view_rows_with_params(db: Session, query: str, params: dict) -> list[dict]:
    result = db.execute(text(query), params)
    return [dict(row) for row in result.mappings().all()]


def fetch_scalar(db: Session, query: str) -> int:
    return db.execute(text(query)).scalar_one()


def fetch_scalar_with_params(db: Session, query: str, params: dict) -> int:
    return db.execute(text(query), params).scalar_one()


def fetch_one_row_with_params(db: Session, query: str, params: dict) -> dict | None:
    result = db.execute(text(query), params).mappings().first()
    return dict(result) if result else None


def fetch_neows_object_detail_row(db: Session, neo_reference_id: str) -> dict | None:
    return fetch_one_row_with_params(
        db,
        """
        WITH object_identity AS (
            SELECT
                b.neo_reference_id,
                b.name,
                b.nasa_jpl_url,
                b.absolute_magnitude_h,
                b.is_potentially_hazardous_asteroid,
                b.is_sentry_object,
                b.estimated_diameter_min_km,
                b.estimated_diameter_max_km,
                b.s_ingested_at
            FROM stg_neows.neo_browse b
            WHERE b.neo_reference_id = :neo_reference_id
            UNION ALL
            SELECT
                l.neo_reference_id,
                l.name,
                l.nasa_jpl_url,
                l.absolute_magnitude_h,
                l.is_potentially_hazardous_asteroid,
                l.is_sentry_object,
                l.estimated_diameter_min_km,
                l.estimated_diameter_max_km,
                l.s_ingested_at
            FROM stg_neows.neo_lookup l
            WHERE l.neo_reference_id = :neo_reference_id
            UNION ALL
            SELECT
                f.neo_reference_id,
                f.name,
                f.nasa_jpl_url,
                f.absolute_magnitude_h,
                f.is_potentially_hazardous_asteroid,
                f.is_sentry_object,
                f.estimated_diameter_min_km,
                f.estimated_diameter_max_km,
                f.s_ingested_at
            FROM stg_neows.neo_feed f
            WHERE f.neo_reference_id = :neo_reference_id
        ),
        best_identity AS (
            SELECT
                neo_reference_id,
                name,
                nasa_jpl_url,
                absolute_magnitude_h,
                is_potentially_hazardous_asteroid,
                is_sentry_object,
                estimated_diameter_min_km,
                estimated_diameter_max_km,
                s_ingested_at
            FROM object_identity
            ORDER BY s_ingested_at DESC NULLS LAST
            LIMIT 1
        ),
        feed_rollup AS (
            SELECT
                neo_reference_id,
                MIN(close_approach_date) AS first_close_approach_date,
                MAX(close_approach_date) AS most_recent_close_approach_date,
                COUNT(*) AS approach_count,
                MIN(miss_distance_kilometers) AS min_miss_distance_km,
                MAX(relative_velocity_km_per_hour) AS max_velocity_kph,
                (
                    ARRAY_AGG(
                        orbiting_body
                        ORDER BY close_approach_date DESC, close_approach_datetime DESC NULLS LAST
                    )
                )[1] AS latest_orbiting_body,
                MAX(s_ingested_at) AS last_ingested_at
            FROM stg_neows.neo_feed
            WHERE neo_reference_id = :neo_reference_id
            GROUP BY neo_reference_id
        )
        SELECT
            COALESCE(i.neo_reference_id, f.neo_reference_id) AS neo_reference_id,
            i.name,
            i.nasa_jpl_url,
            i.absolute_magnitude_h,
            i.is_potentially_hazardous_asteroid,
            i.is_sentry_object,
            i.estimated_diameter_min_km,
            i.estimated_diameter_max_km,
            f.first_close_approach_date,
            f.most_recent_close_approach_date,
            COALESCE(f.approach_count, 0) AS approach_count,
            f.min_miss_distance_km,
            f.max_velocity_kph,
            f.latest_orbiting_body,
            COALESCE(f.last_ingested_at, i.s_ingested_at) AS last_ingested_at
        FROM best_identity i
        FULL OUTER JOIN feed_rollup f
            ON f.neo_reference_id = i.neo_reference_id
        """,
        {"neo_reference_id": neo_reference_id},
    )


@router.get("/catalog", response_model=AnalyticsCatalogResponse)
def get_analytics_catalog():
    return {"endpoints": ANALYTICS_ENDPOINTS}


@router.get("/ingestion-status", response_model=list[IngestionStatusResponse])
def list_ingestion_status(db: Session = Depends(get_db)):
    return fetch_view_rows(
        db,
        """
        SELECT
            source_name,
            source_endpoint,
            latest_run_started_at,
            latest_run_finished_at,
            latest_status,
            latest_records_inserted,
            created_at
        FROM dmt_generic.v_dmt_ingestion_status
        ORDER BY source_name, source_endpoint
        """,
    )


@router.get("/neows/daily-summary", response_model=list[NeoWsDailySummaryResponse])
def list_neows_daily_summary(db: Session = Depends(get_db)):
    return fetch_view_rows(
        db,
        """
        SELECT
            close_approach_date,
            neo_count,
            hazardous_count,
            distinct_object_count,
            avg_velocity_km_per_hour,
            min_miss_distance_kilometers,
            max_miss_distance_kilometers,
            biggest_estimated_diameter_max_km
        FROM dmt_generic.v_dmt_neows_daily_summary
        ORDER BY close_approach_date DESC
        """,
    )


@router.get("/neows/kpis", response_model=list[NeoWsKpiResponse])
def list_neows_kpis(db: Session = Depends(get_db)):
    return fetch_view_rows(
        db,
        """
        SELECT
            category,
            object_id,
            object_name,
            est_max_diameter_m,
            velocity_kph,
            recent_approach_date,
            is_hazardous_flag,
            miss_distance_km,
            value
        FROM dmt_generic.v_dmt_neows_kpis
        ORDER BY category
        """,
    )


@router.get("/neows/object/{neo_reference_id}", response_model=NeoWsObjectDetailResponse)
def get_neows_object_detail(neo_reference_id: str, db: Session = Depends(get_db)):
    row = fetch_neows_object_detail_row(db, neo_reference_id)

    if row is None or row["neo_reference_id"] is None:
        raise HTTPException(status_code=404, detail="NeoWs object not found")

    return row


@router.get("/neows/objects", response_model=list[NeoWsObjectSearchResultResponse])
def search_neows_objects(
    query: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    search_term = (query or "").strip()
    search_pattern = f"%{search_term}%"
    prefix_pattern = f"{search_term}%"
    return fetch_view_rows_with_params(
        db,
        """
        WITH object_candidates AS (
            SELECT
                b.neo_reference_id,
                b.name,
                b.is_potentially_hazardous_asteroid,
                b.s_ingested_at
            FROM stg_neows.neo_browse b
            UNION ALL
            SELECT
                l.neo_reference_id,
                l.name,
                l.is_potentially_hazardous_asteroid,
                l.s_ingested_at
            FROM stg_neows.neo_lookup l
            UNION ALL
            SELECT
                f.neo_reference_id,
                f.name,
                f.is_potentially_hazardous_asteroid,
                f.s_ingested_at
            FROM stg_neows.neo_feed f
        ),
        latest_objects AS (
            SELECT
                neo_reference_id,
                name,
                is_potentially_hazardous_asteroid,
                s_ingested_at,
                ROW_NUMBER() OVER (
                    PARTITION BY neo_reference_id
                    ORDER BY s_ingested_at DESC NULLS LAST
                ) AS rn
            FROM object_candidates
        ),
        feed_rollup AS (
            SELECT
                neo_reference_id,
                MAX(close_approach_date) AS most_recent_close_approach_date,
                COUNT(*) AS approach_count
            FROM stg_neows.neo_feed
            GROUP BY neo_reference_id
        )
        SELECT
            o.neo_reference_id,
            o.name,
            o.is_potentially_hazardous_asteroid,
            f.most_recent_close_approach_date,
            COALESCE(f.approach_count, 0) AS approach_count
        FROM latest_objects o
        LEFT JOIN feed_rollup f
            ON f.neo_reference_id = o.neo_reference_id
        WHERE o.rn = 1
          AND (
              CAST(:query AS text) IS NULL
              OR o.neo_reference_id ILIKE CAST(:search_pattern AS text)
              OR o.name ILIKE CAST(:search_pattern AS text)
          )
        ORDER BY
            CASE
                WHEN CAST(:query AS text) IS NULL THEN 4
                WHEN o.neo_reference_id = CAST(:query AS text) THEN 0
                WHEN o.name = CAST(:query AS text) THEN 1
                WHEN o.neo_reference_id ILIKE CAST(:prefix_pattern AS text) THEN 2
                WHEN o.name ILIKE CAST(:prefix_pattern AS text) THEN 3
                ELSE 4
            END,
            f.most_recent_close_approach_date DESC NULLS LAST,
            o.s_ingested_at DESC NULLS LAST,
            o.name
        LIMIT :limit
        """,
        {
            "query": search_term or None,
            "search_pattern": search_pattern,
            "prefix_pattern": prefix_pattern,
            "limit": limit,
        },
    )


def build_neows_live_summary(
    name: str,
    neo_reference_id: str,
    is_hazardous: bool | None,
    estimated_diameter_min_km: float | None,
    estimated_diameter_max_km: float | None,
    latest_close_approach_date,
    latest_orbiting_body: str | None,
    latest_miss_distance_km: float | None,
    latest_relative_velocity_kph: float | None,
) -> str:
    hazard_phrase = (
        "NASA currently flags it as potentially hazardous."
        if is_hazardous is True
        else "NASA does not currently flag it as potentially hazardous."
        if is_hazardous is False
        else "Its current hazard flag is not available."
    )
    size_phrase = (
        f"Its estimated size ranges from about {estimated_diameter_min_km:.3f} km to {estimated_diameter_max_km:.3f} km."
        if estimated_diameter_min_km is not None and estimated_diameter_max_km is not None
        else "Its estimated size range is not available in the live payload."
    )
    approach_phrase = (
        f"The latest close-approach record is dated {latest_close_approach_date}"
        f"{f' around {latest_orbiting_body}' if latest_orbiting_body else ''}."
        if latest_close_approach_date is not None
        else "No close-approach record is present in the live lookup payload."
    )
    motion_phrase = (
        f"The latest recorded miss distance is about {latest_miss_distance_km:,.0f} km and the relative velocity is about {latest_relative_velocity_kph:,.0f} kph."
        if latest_miss_distance_km is not None and latest_relative_velocity_kph is not None
        else "Detailed latest motion metrics are not fully available in the live lookup payload."
    )
    return (
        f"{name} ({neo_reference_id}) is a Near-Earth Object in NASA's live NeoWs service. "
        f"{hazard_phrase} {size_phrase} {approach_phrase} {motion_phrase}"
    )


def fetch_eonet_event_detail_row(db: Session, event_id: str) -> dict | None:
    return fetch_one_row_with_params(
        db,
        """
        WITH latest_event AS (
            SELECT
                e.event_id,
                e.title,
                e.description,
                e.link,
                e.closed,
                e.categories,
                e.sources,
                e.geometry,
                e.s_ingested_at,
                ROW_NUMBER() OVER (
                    PARTITION BY e.event_id
                    ORDER BY e.s_ingested_at DESC NULLS LAST, e.id DESC
                ) AS rn
            FROM stg_eonet.events e
            WHERE e.event_id = :event_id
        )
        SELECT
            event_id,
            title,
            description,
            link,
            CASE WHEN closed IS NULL THEN 'open' ELSE 'closed' END AS event_status,
            closed AS closed_at,
            COALESCE(jsonb_array_length(COALESCE(categories, '[]'::jsonb)), 0) AS category_count,
            (
                SELECT string_agg(cat.value ->> 'title', ', ' ORDER BY cat.value ->> 'title')
                FROM jsonb_array_elements(COALESCE(categories, '[]'::jsonb)) AS cat(value)
            ) AS category_titles,
            COALESCE(jsonb_array_length(COALESCE(sources, '[]'::jsonb)), 0) AS source_count,
            (
                SELECT string_agg(src.value ->> 'id', ', ' ORDER BY src.value ->> 'id')
                FROM jsonb_array_elements(COALESCE(sources, '[]'::jsonb)) AS src(value)
            ) AS source_titles,
            COALESCE(jsonb_array_length(COALESCE(geometry, '[]'::jsonb)), 0) AS geometry_count,
            (
                SELECT MAX(NULLIF(geom.value ->> 'date', '')::timestamptz)
                FROM jsonb_array_elements(COALESCE(geometry, '[]'::jsonb)) AS geom(value)
            ) AS latest_geometry_at,
            s_ingested_at AS last_ingested_at
        FROM latest_event
        WHERE rn = 1
        """,
        {"event_id": event_id},
    )


def build_eonet_insight(detail: dict, mode: str) -> dict:
    if mode == "operations":
        summary = (
            f"{detail['title']} ({detail['event_id']}) is currently {detail['event_status']}. "
            f"It spans {detail['category_count']} categor{'y' if detail['category_count'] == 1 else 'ies'}"
            f" and has {detail['geometry_count']} recorded geometry update"
            f"{'' if detail['geometry_count'] == 1 else 's'} in NASAHub. "
            f"{f'The latest recorded activity is {detail['latest_geometry_at']}. ' if detail['latest_geometry_at'] else ''}"
            "This view is grounded in the latest staged EONET event snapshot."
        )
        title = "Operational Event Context"
    else:
        summary = (
            f"{detail['title']} ({detail['event_id']}) is an EONET event tracked in NASAHub. "
            f"It is categorized under {detail['category_titles'] or 'unclassified categories'}"
            f" and currently appears as {detail['event_status']}. "
            f"{f'Its description is: {detail['description']} ' if detail['description'] else ''}"
            "This explanation is grounded in NASAHub’s latest curated EONET event view."
        )
        title = "Event Overview"
    return {
        "event_id": detail["event_id"],
        "mode": mode,
        "title": title,
        "summary": summary,
        "sources": ["nasahub_local"],
    }


def fetch_exoplanet_planet_detail_row(db: Session, pl_name: str) -> dict | None:
    return fetch_one_row_with_params(
        db,
        """
        SELECT
            pl_name,
            hostname,
            discovery_method,
            disc_year,
            disc_facility,
            sy_dist,
            pl_orbper,
            pl_rade,
            pl_bmasse,
            st_teff,
            last_ingested_at
        FROM dmt_generic.v_dmt_exoplanet_catalog
        WHERE pl_name = :pl_name
        """,
        {"pl_name": pl_name},
    )


def build_exoplanet_insight(detail: dict, mode: str) -> dict:
    if mode == "discovery":
        summary = (
            f"{detail['pl_name']} was recorded in NASAHub as discovered via {detail['discovery_method']}"
            f"{f' in {detail['disc_year']}' if detail['disc_year'] is not None else ''}"
            f"{f' using {detail['disc_facility']}' if detail['disc_facility'] else ''}. "
            f"{f'Its host star is {detail['hostname']}. ' if detail['hostname'] else ''}"
            "This description is grounded in the curated exoplanet catalog."
        )
        title = "Discovery Context"
    elif mode == "science":
        summary = (
            f"{detail['pl_name']} scientific context from NASAHub: "
            f"{f'orbital period about {detail['pl_orbper']:.2f} days; ' if detail['pl_orbper'] is not None else ''}"
            f"{f'radius about {detail['pl_rade']:.2f} Earth radii; ' if detail['pl_rade'] is not None else ''}"
            f"{f'mass about {detail['pl_bmasse']:.2f} Earth masses; ' if detail['pl_bmasse'] is not None else ''}"
            f"{f'distance about {detail['sy_dist']:.2f} parsecs.' if detail['sy_dist'] is not None else 'distance is not available in the current curated row.'}"
        )
        title = "Scientific Context"
    else:
        summary = (
            f"{detail['pl_name']} is an exoplanet in NASAHub’s curated catalog. "
            f"{f'It orbits {detail['hostname']}. ' if detail['hostname'] else ''}"
            f"{f'The catalog places it about {detail['sy_dist']:.2f} parsecs away. ' if detail['sy_dist'] is not None else ''}"
            f"It is associated with the {detail['discovery_method']} discovery method. "
            "This overview is grounded in NASAHub’s curated exoplanet data."
        )
        title = "Planet Overview"
    return {
        "pl_name": detail["pl_name"],
        "mode": mode,
        "title": title,
        "summary": summary,
        "sources": ["nasahub_local"],
    }


def build_ask_citations(
    source: str,
    entity_id: str,
    include_live_enrichment: bool,
    live_payload: dict | None = None,
) -> list[dict]:
    citations = []
    if source == "neows":
        citations.append(
            AskNasaHubCitation(
                source="nasahub_local",
                title="NASAHub curated NeoWs object profile",
                entity_id=entity_id,
                path=f"/analytics/neows/object/{entity_id}",
                source_url=None,
                note="Trusted local detail and analytics from the Lenovo-hosted curated layer.",
            ).model_dump()
        )
        citations.append(
            AskNasaHubCitation(
                source="nasahub_local",
                title="NASAHub NeoWs object insight",
                entity_id=entity_id,
                path=f"/analytics/neows/object/{entity_id}/insight?mode=overview",
                source_url=None,
                note="Local summary used before any external enrichment.",
            ).model_dump()
        )
        if include_live_enrichment and live_payload:
            citations.append(
                AskNasaHubCitation(
                    source="nasa_neows_live",
                    title="NASA NeoWs live lookup",
                    entity_id=entity_id,
                    path=f"/analytics/neows/object/{entity_id}/live-enrichment",
                    source_url=live_payload.get("source_url"),
                    note="Optional live NASA enrichment layered on top of NASAHub local retrieval.",
                ).model_dump()
            )
    elif source == "eonet":
        citations.append(
            AskNasaHubCitation(
                source="nasahub_local",
                title="NASAHub curated EONET event detail",
                entity_id=entity_id,
                path=f"/analytics/eonet/event/{entity_id}",
                source_url=None,
                note="Trusted local event profile from the curated EONET layer.",
            ).model_dump()
        )
        citations.append(
            AskNasaHubCitation(
                source="nasahub_local",
                title="NASAHub EONET event insight",
                entity_id=entity_id,
                path=f"/analytics/eonet/event/{entity_id}/insight?mode=overview",
                source_url=None,
                note="Overview guidance grounded in the local event record.",
            ).model_dump()
        )
    else:
        encoded_name = requests.utils.quote(entity_id, safe="")
        citations.append(
            AskNasaHubCitation(
                source="nasahub_local",
                title="NASAHub curated exoplanet detail",
                entity_id=entity_id,
                path=f"/analytics/exoplanet/planet/{encoded_name}",
                source_url=None,
                note="Trusted local planet profile from the curated exoplanet catalog.",
            ).model_dump()
        )
        citations.append(
            AskNasaHubCitation(
                source="nasahub_local",
                title="NASAHub exoplanet insight",
                entity_id=entity_id,
                path=f"/analytics/exoplanet/planet/{encoded_name}/insight?mode=overview",
                source_url=None,
                note="Overview guidance grounded in the local planet record.",
            ).model_dump()
        )
    return citations


def trim_chat_history(history: list[AskNasaHubMessage]) -> list[dict]:
    trimmed = history[-6:]
    return [{"role": item.role, "content": item.content} for item in trimmed]


def infer_general_source(question: str) -> str:
    normalized = question.lower()
    if any(
        token in normalized
        for token in [
            "neo",
            "asteroid",
            "near earth",
            "near-earth",
            "close to earth",
            "hazardous",
            "miss distance",
            "approach",
        ]
    ):
        return "neows"
    if any(
        token in normalized
        for token in [
            "event",
            "storm",
            "wildfire",
            "volcano",
            "earthquake",
            "category",
            "eonet",
        ]
    ):
        return "eonet"
    if any(
        token in normalized
        for token in [
            "planet",
            "exoplanet",
            "discovery",
            "host star",
            "orbital",
            "radius",
            "mass",
        ]
    ):
        return "exoplanet"
    return "general"


def infer_general_intent(source: str, question: str) -> str:
    normalized = question.lower()
    if source == "neows":
        if any(token in normalized for token in ["biggest", "largest", "size", "diameter"]):
            return "largest"
        if any(token in normalized for token in ["closest", "nearest", "close to earth", "miss distance"]):
            return "closest"
        if any(token in normalized for token in ["fastest", "speed", "velocity"]):
            return "fastest"
        if any(token in normalized for token in ["hazard", "hazardous", "dangerous"]):
            return "hazardous"
        return "largest"
    if source == "eonet":
        if any(token in normalized for token in ["open", "active", "ongoing"]):
            return "open"
        if any(token in normalized for token in ["latest", "newest", "recent", "current"]):
            return "latest"
        if "category" in normalized or "categories" in normalized:
            return "category"
        return "latest"
    if source == "exoplanet":
        if any(token in normalized for token in ["closest", "nearest", "nearby", "distance"]):
            return "nearest"
        if any(token in normalized for token in ["biggest", "largest", "radius", "mass"]):
            return "largest"
        if any(token in normalized for token in ["method", "discovery method"]):
            return "method"
        if any(token in normalized for token in ["newest", "latest", "recent", "year"]):
            return "newest"
        return "nearest"
    return "overview"


def build_match(source: str, entity_id: str, title: str, path: str, note: str, rank_reason: str, metric_label: str | None = None, metric_value: str | None = None) -> dict:
    return AskNasaHubMatch(
        source=source,
        entity_id=entity_id,
        title=title,
        path=path,
        note=note,
        rank_reason=rank_reason,
        metric_label=metric_label,
        metric_value=metric_value,
    ).model_dump()


def fetch_neows_general_context(db: Session, include_live_enrichment: bool, intent: str) -> tuple[dict, list[str], list[dict], list[dict]]:
    largest_objects = fetch_view_rows(
        db,
        """
        SELECT
            neo_reference_id AS entity_id,
            name AS title,
            MAX(estimated_diameter_max_km) * 1000 AS est_max_diameter_m,
            MIN(miss_distance_kilometers) AS min_miss_distance_km,
            MAX(relative_velocity_km_per_hour) AS max_velocity_kph,
            MAX(close_approach_date) AS most_recent_close_approach_date,
            BOOL_OR(is_potentially_hazardous_asteroid) AS is_hazardous_flag
        FROM stg_neows.neo_feed
        GROUP BY neo_reference_id, name
        ORDER BY est_max_diameter_m DESC NULLS LAST, most_recent_close_approach_date DESC NULLS LAST, neo_reference_id
        LIMIT 5
        """,
    )
    fastest_objects = fetch_view_rows(
        db,
        """
        SELECT
            neo_reference_id AS entity_id,
            name AS title,
            MAX(relative_velocity_km_per_hour) AS max_velocity_kph,
            MAX(estimated_diameter_max_km) * 1000 AS est_max_diameter_m,
            MIN(miss_distance_kilometers) AS min_miss_distance_km,
            MAX(close_approach_date) AS most_recent_close_approach_date
        FROM stg_neows.neo_feed
        GROUP BY neo_reference_id, name
        ORDER BY max_velocity_kph DESC NULLS LAST, most_recent_close_approach_date DESC NULLS LAST, neo_reference_id
        LIMIT 5
        """,
    )
    closest_objects = fetch_view_rows(
        db,
        """
        SELECT
            neo_reference_id AS entity_id,
            name AS title,
            MIN(miss_distance_kilometers) AS min_miss_distance_km,
            MAX(estimated_diameter_max_km) * 1000 AS est_max_diameter_m,
            MAX(relative_velocity_km_per_hour) AS max_velocity_kph,
            MAX(close_approach_date) AS most_recent_close_approach_date
        FROM stg_neows.neo_feed
        GROUP BY neo_reference_id, name
        ORDER BY min_miss_distance_km ASC NULLS LAST, most_recent_close_approach_date DESC NULLS LAST, neo_reference_id
        LIMIT 5
        """,
    )
    recent_daily_summary = fetch_view_rows(
        db,
        """
        SELECT
            close_approach_date,
            neo_count,
            hazardous_count,
            distinct_object_count,
            avg_velocity_km_per_hour,
            min_miss_distance_kilometers,
            max_miss_distance_kilometers,
            biggest_estimated_diameter_max_km
        FROM dmt_generic.v_dmt_neows_daily_summary
        ORDER BY close_approach_date DESC
        LIMIT 7
        """,
    )

    intent_map = {
        "largest": ("largest_objects", largest_objects, "estimated maximum diameter", "est_max_diameter_m", "m"),
        "fastest": ("fastest_objects", fastest_objects, "maximum recorded velocity", "max_velocity_kph", "kph"),
        "closest": ("closest_objects", closest_objects, "closest recorded miss distance", "min_miss_distance_km", "km"),
        "hazardous": ("largest_objects", [item for item in largest_objects if item.get("is_hazardous_flag")], "estimated maximum diameter", "est_max_diameter_m", "m"),
    }
    selected_key, selected_rows, metric_label, metric_field, metric_suffix = intent_map.get(
        intent,
        ("largest_objects", largest_objects, "estimated maximum diameter", "est_max_diameter_m", "m"),
    )
    if not selected_rows:
        selected_rows = largest_objects

    live_enrichment = None
    grounded_sources = ["nasahub_local"]
    if include_live_enrichment and selected_rows and selected_rows[0].get("entity_id"):
        try:
            live_enrichment = fetch_neows_live_enrichment_payload(selected_rows[0]["entity_id"])
            grounded_sources.append("nasa_neows_live")
        except HTTPException:
            live_enrichment = None

    citations = [
        AskNasaHubCitation(
            source="nasahub_local",
            title="NASAHub NeoWs general rankings",
            entity_id=None,
            path="/analytics/neows/kpis",
            source_url=None,
            note="General NeoWs retrieval combines curated KPI-style rankings and feed aggregations.",
        ).model_dump(),
        AskNasaHubCitation(
            source="nasahub_local",
            title="NASAHub NeoWs daily summary",
            entity_id=None,
            path="/analytics/neows/daily-summary",
            source_url=None,
            note="Recent daily context for close-approach activity.",
        ).model_dump(),
    ]
    if live_enrichment:
        citations.append(
            AskNasaHubCitation(
                source="nasa_neows_live",
                title="NASA NeoWs live lookup for top ranked object",
                entity_id=selected_rows[0]["entity_id"],
                path=f"/analytics/neows/object/{selected_rows[0]['entity_id']}/live-enrichment",
                source_url=live_enrichment.get("source_url"),
                note="Optional live enrichment for the top NeoWs candidate returned by general retrieval.",
            ).model_dump()
        )

    matched_entities = [
        build_match(
            source="neows",
            entity_id=item["entity_id"],
            title=item["title"],
            path=f"/analytics/neows/object/{item['entity_id']}",
            note=f"Top NeoWs candidate for the '{intent}' intent in NASAHub local data.",
            rank_reason=f"Ranked using {metric_label}.",
            metric_label=metric_label,
            metric_value=(
                f"{item.get(metric_field):,.1f} {metric_suffix}"
                if item.get(metric_field) is not None
                else "n/a"
            ),
        )
        for item in selected_rows[:3]
    ]
    return (
        {
            "intent": intent,
            "primary_ranking": selected_key,
            "largest_objects": largest_objects,
            "fastest_objects": fastest_objects,
            "closest_objects": closest_objects,
            "recent_daily_summary": recent_daily_summary,
            "live_enrichment_top_match": live_enrichment,
        },
        grounded_sources,
        citations,
        matched_entities,
    )


def fetch_eonet_general_context(db: Session, intent: str) -> tuple[dict, list[str], list[dict], list[dict]]:
    category_summary = fetch_view_rows(
        db,
        """
        SELECT
            category_id,
            category_title,
            total_events,
            open_events,
            closed_events,
            total_sources,
            latest_geometry_at,
            last_ingested_at
        FROM dmt_generic.v_dmt_eonet_category_summary
        ORDER BY total_events DESC, category_id
        LIMIT 8
        """,
    )
    recent_events = fetch_view_rows(
        db,
        """
        SELECT
            event_id,
            title,
            event_status,
            category_titles,
            source_count,
            geometry_count,
            latest_geometry_at,
            last_ingested_at
        FROM dmt_generic.v_dmt_eonet_event_overview
        ORDER BY latest_geometry_at DESC NULLS LAST, event_id
        LIMIT 5
        """,
    )
    open_events = [item for item in recent_events if item.get("event_status") == "open"]
    category_leaders = category_summary[:5]
    citations = [
        AskNasaHubCitation(
            source="nasahub_local",
            title="NASAHub EONET category summary",
            entity_id=None,
            path="/analytics/eonet/category-summary",
            source_url=None,
            note="General category-level operational view across EONET events.",
        ).model_dump(),
        AskNasaHubCitation(
            source="nasahub_local",
            title="NASAHub EONET event overview",
            entity_id=None,
            path="/analytics/eonet/event-overview",
            source_url=None,
            note="Recent event-level overview used for general retrieval.",
        ).model_dump(),
    ]
    if intent == "open":
        selected_events = open_events or recent_events
        matched_entities = [
            build_match(
                source="eonet",
                entity_id=item["event_id"],
                title=item["title"],
                path=f"/analytics/eonet/event/{item['event_id']}",
                note="Open EONET event surfaced by general retrieval.",
                rank_reason="Ranked by open status and latest geometry timestamp.",
                metric_label="latest activity",
                metric_value=str(item.get("latest_geometry_at") or "n/a"),
            )
            for item in selected_events[:3]
        ]
    elif intent == "category":
        matched_entities = [
            build_match(
                source="eonet",
                entity_id=item["category_id"],
                title=item["category_title"],
                path="/analytics/eonet/category-summary",
                note="Leading EONET category surfaced by general retrieval.",
                rank_reason="Ranked by total event count.",
                metric_label="total events",
                metric_value=str(item.get("total_events")),
            )
            for item in category_leaders[:3]
        ]
    else:
        matched_entities = [
            build_match(
                source="eonet",
                entity_id=item["event_id"],
                title=item["title"],
                path=f"/analytics/eonet/event/{item['event_id']}",
                note="Recent EONET event surfaced by general retrieval.",
                rank_reason="Ranked by latest geometry timestamp.",
                metric_label="latest activity",
                metric_value=str(item.get("latest_geometry_at") or "n/a"),
            )
            for item in recent_events[:3]
        ]
    return (
        {
            "intent": intent,
            "category_summary": category_summary,
            "recent_events": recent_events,
        },
        ["nasahub_local"],
        citations,
        matched_entities,
    )


def fetch_exoplanet_general_context(db: Session, intent: str) -> tuple[dict, list[str], list[dict], list[dict]]:
    discovery_method_summary = fetch_view_rows(
        db,
        """
        SELECT
            discovery_method,
            planet_count,
            distinct_host_count,
            first_disc_year,
            last_disc_year,
            avg_distance_pc
        FROM dmt_generic.v_dmt_exoplanet_discovery_method_summary
        ORDER BY planet_count DESC, discovery_method
        LIMIT 8
        """,
    )
    yearly_summary = fetch_view_rows(
        db,
        """
        SELECT
            disc_year,
            planet_count,
            distinct_host_count,
            avg_distance_pc,
            cumulative_planet_count
        FROM dmt_generic.v_dmt_exoplanet_discovery_yearly_summary
        ORDER BY disc_year DESC
        LIMIT 10
        """,
    )
    nearest_planets = fetch_view_rows(
        db,
        """
        SELECT
            pl_name AS entity_id,
            pl_name AS title,
            hostname,
            discovery_method,
            disc_year,
            sy_dist,
            pl_rade,
            pl_bmasse
        FROM dmt_generic.v_dmt_exoplanet_catalog
        ORDER BY sy_dist NULLS LAST, pl_name
        LIMIT 5
        """,
    )
    largest_planets = fetch_view_rows(
        db,
        """
        SELECT
            pl_name AS entity_id,
            pl_name AS title,
            hostname,
            discovery_method,
            disc_year,
            sy_dist,
            pl_rade,
            pl_bmasse
        FROM dmt_generic.v_dmt_exoplanet_catalog
        ORDER BY pl_rade DESC NULLS LAST, pl_bmasse DESC NULLS LAST, pl_name
        LIMIT 5
        """,
    )
    newest_planets = fetch_view_rows(
        db,
        """
        SELECT
            pl_name AS entity_id,
            pl_name AS title,
            hostname,
            discovery_method,
            disc_year,
            sy_dist,
            pl_rade,
            pl_bmasse
        FROM dmt_generic.v_dmt_exoplanet_catalog
        ORDER BY disc_year DESC NULLS LAST, pl_name
        LIMIT 5
        """,
    )
    citations = [
        AskNasaHubCitation(
            source="nasahub_local",
            title="NASAHub exoplanet discovery method summary",
            entity_id=None,
            path="/analytics/exoplanet/discovery-method-summary",
            source_url=None,
            note="General discovery-method context across the curated exoplanet catalog.",
        ).model_dump(),
        AskNasaHubCitation(
            source="nasahub_local",
            title="NASAHub exoplanet discovery yearly summary",
            entity_id=None,
            path="/analytics/exoplanet/discovery-yearly-summary",
            source_url=None,
            note="General yearly trend context across the curated exoplanet catalog.",
        ).model_dump(),
    ]
    if intent == "largest":
        selected_planets = largest_planets
        matched_entities = [
            build_match(
                source="exoplanet",
                entity_id=item["entity_id"],
                title=item["title"],
                path=f"/analytics/exoplanet/planet/{requests.utils.quote(item['entity_id'], safe='')}",
                note="Large exoplanet surfaced by general retrieval.",
                rank_reason="Ranked by planetary radius, then mass.",
                metric_label="radius",
                metric_value=f"{item.get('pl_rade', 'n/a')} Earth radii" if item.get("pl_rade") is not None else "n/a",
            )
            for item in selected_planets[:3]
        ]
    elif intent == "newest":
        selected_planets = newest_planets
        matched_entities = [
            build_match(
                source="exoplanet",
                entity_id=item["entity_id"],
                title=item["title"],
                path=f"/analytics/exoplanet/planet/{requests.utils.quote(item['entity_id'], safe='')}",
                note="Recently discovered exoplanet surfaced by general retrieval.",
                rank_reason="Ranked by discovery year descending.",
                metric_label="discovery year",
                metric_value=str(item.get("disc_year") or "n/a"),
            )
            for item in selected_planets[:3]
        ]
    elif intent == "method":
        matched_entities = [
            build_match(
                source="exoplanet",
                entity_id=item["discovery_method"],
                title=item["discovery_method"],
                path="/analytics/exoplanet/discovery-method-summary",
                note="Leading discovery method surfaced by general retrieval.",
                rank_reason="Ranked by planet count.",
                metric_label="planet count",
                metric_value=str(item.get("planet_count")),
            )
            for item in discovery_method_summary[:3]
        ]
    else:
        selected_planets = nearest_planets
        matched_entities = [
            build_match(
                source="exoplanet",
                entity_id=item["entity_id"],
                title=item["title"],
                path=f"/analytics/exoplanet/planet/{requests.utils.quote(item['entity_id'], safe='')}",
                note="Nearby catalog planet surfaced by general exoplanet retrieval.",
                rank_reason="Ranked by distance from Earth.",
                metric_label="distance",
                metric_value=f"{item.get('sy_dist', 'n/a')} pc" if item.get("sy_dist") is not None else "n/a",
            )
            for item in selected_planets[:3]
        ]
    return (
        {
            "intent": intent,
            "discovery_method_summary": discovery_method_summary,
            "yearly_summary": yearly_summary,
            "nearest_planets": nearest_planets,
            "largest_planets": largest_planets,
            "newest_planets": newest_planets,
        },
        ["nasahub_local"],
        citations,
        matched_entities,
    )


def build_general_context(payload: AskNasaHubRequest, db: Session) -> tuple[str, dict, list[str], list[dict], list[dict]]:
    requested_source = payload.source or "general"
    resolved_source = requested_source
    if requested_source == "general":
        resolved_source = infer_general_source(payload.question)
    intent = infer_general_intent(resolved_source, payload.question)

    if resolved_source == "neows":
        context_payload, grounded_sources, citations, matched_entities = fetch_neows_general_context(
            db,
            payload.include_live_enrichment,
            intent,
        )
        return "neows", context_payload, grounded_sources, citations, matched_entities
    if resolved_source == "eonet":
        context_payload, grounded_sources, citations, matched_entities = fetch_eonet_general_context(db, intent)
        return "eonet", context_payload, grounded_sources, citations, matched_entities
    if resolved_source == "exoplanet":
        context_payload, grounded_sources, citations, matched_entities = fetch_exoplanet_general_context(db, intent)
        return "exoplanet", context_payload, grounded_sources, citations, matched_entities

    neows_context = fetch_neows_general_context(db, payload.include_live_enrichment, infer_general_intent("neows", payload.question))
    eonet_context = fetch_eonet_general_context(db, infer_general_intent("eonet", payload.question))
    exoplanet_context = fetch_exoplanet_general_context(db, infer_general_intent("exoplanet", payload.question))
    context_payload = {
        "neows": neows_context[0],
        "eonet": eonet_context[0],
        "exoplanet": exoplanet_context[0],
    }
    grounded_sources = sorted(
        {
            *neows_context[1],
            *eonet_context[1],
            *exoplanet_context[1],
        }
    )
    citations = [*neows_context[2], *eonet_context[2], *exoplanet_context[2]]
    matched_entities = [*neows_context[3], *eonet_context[3], *exoplanet_context[3]]
    return "general", context_payload, grounded_sources, citations, matched_entities


def call_openai_grounded_answer(
    source: str,
    entity_id: str,
    question: str,
    context_payload: dict,
    chat_history: list[dict] | None = None,
) -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")

    instructions = (
        "You are NASAHub Assistant for a private analytics dashboard running on the Lenovo server. "
        "Always use retrieval-first behavior: base the answer on the supplied NASAHub context first, "
        "and use live enrichment only if it is explicitly present in the context. "
        "If the supplied context is insufficient, say exactly what is missing instead of guessing. "
        "Do not invent facts, links, dates, or measurements. Keep the answer concise, operationally useful, "
        "and suitable for an internal dashboard user. Mention when a statement comes from NASAHub local data "
        "versus optional live enrichment if that distinction matters."
    )
    history_payload = chat_history or []
    input_text = (
        f"Source: {source}\n"
        f"Entity: {entity_id}\n"
        f"User question: {question}\n\n"
        f"Recent conversation JSON:\n{json.dumps(history_payload, default=str)}\n\n"
        f"Grounded context JSON:\n{json.dumps(context_payload, default=str)}"
    )
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "instructions": instructions,
                "input": input_text,
            },
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="OpenAI request failed") from exc

    payload = response.json()
    if payload.get("output_text"):
        return payload["output_text"]

    output_parts = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text_value = content.get("text")
            if text_value:
                output_parts.append(text_value)
    if output_parts:
        return "\n".join(output_parts)
    raise HTTPException(status_code=502, detail="OpenAI returned no text output")


def fetch_neows_live_enrichment_payload(neo_reference_id: str) -> dict:
    if not NASA_API_KEY:
        raise HTTPException(status_code=503, detail="NASA_API_KEY is not configured")

    try:
        response = requests.get(
            f"{NEOWS_LOOKUP_URL}/{neo_reference_id}",
            params={"api_key": NASA_API_KEY},
            timeout=30,
        )
        response.raise_for_status()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        if status_code == 404:
            raise HTTPException(status_code=404, detail="Live NeoWs object not found") from exc
        raise HTTPException(status_code=502, detail="Live NASA NeoWs lookup failed") from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="Live NASA NeoWs lookup failed") from exc

    payload = response.json()
    estimated_diameter_km = payload.get("estimated_diameter", {}).get("kilometers", {})
    close_approach_data = payload.get("close_approach_data") or []
    latest_close_approach = None
    if close_approach_data:
        latest_close_approach = max(
            close_approach_data,
            key=lambda item: item.get("close_approach_date") or "",
        )

    latest_velocity_kph = None
    latest_miss_distance_km = None
    latest_orbiting_body = None
    latest_close_approach_date = None
    if latest_close_approach:
        latest_close_approach_date = latest_close_approach.get("close_approach_date")
        latest_orbiting_body = latest_close_approach.get("orbiting_body")
        latest_velocity_kph_raw = (
            latest_close_approach.get("relative_velocity", {}).get("kilometers_per_hour")
        )
        latest_miss_distance_km_raw = (
            latest_close_approach.get("miss_distance", {}).get("kilometers")
        )
        latest_velocity_kph = float(latest_velocity_kph_raw) if latest_velocity_kph_raw else None
        latest_miss_distance_km = float(latest_miss_distance_km_raw) if latest_miss_distance_km_raw else None

    estimated_diameter_min_km = estimated_diameter_km.get("estimated_diameter_min")
    estimated_diameter_max_km = estimated_diameter_km.get("estimated_diameter_max")
    name = payload.get("name") or payload.get("neo_reference_id")
    generated_summary = build_neows_live_summary(
        name=name,
        neo_reference_id=payload.get("neo_reference_id"),
        is_hazardous=payload.get("is_potentially_hazardous_asteroid"),
        estimated_diameter_min_km=estimated_diameter_min_km,
        estimated_diameter_max_km=estimated_diameter_max_km,
        latest_close_approach_date=latest_close_approach_date,
        latest_orbiting_body=latest_orbiting_body,
        latest_miss_distance_km=latest_miss_distance_km,
        latest_relative_velocity_kph=latest_velocity_kph,
    )

    return {
        "neo_reference_id": payload.get("neo_reference_id"),
        "name": name,
        "source": "nasa_neows_live",
        "source_url": f"{NEOWS_LOOKUP_URL}/{neo_reference_id}",
        "generated_summary": generated_summary,
        "nasa_jpl_url": payload.get("nasa_jpl_url"),
        "absolute_magnitude_h": payload.get("absolute_magnitude_h"),
        "is_potentially_hazardous_asteroid": payload.get("is_potentially_hazardous_asteroid"),
        "estimated_diameter_min_km": estimated_diameter_min_km,
        "estimated_diameter_max_km": estimated_diameter_max_km,
        "latest_close_approach_date": latest_close_approach_date,
        "latest_orbiting_body": latest_orbiting_body,
        "latest_relative_velocity_kph": latest_velocity_kph,
        "latest_miss_distance_km": latest_miss_distance_km,
    }


@router.get(
    "/neows/object/{neo_reference_id}/live-enrichment",
    response_model=NeoWsLiveEnrichmentResponse,
)
def get_neows_object_live_enrichment(neo_reference_id: str):
    return fetch_neows_live_enrichment_payload(neo_reference_id)


@router.get(
    "/neows/object/{neo_reference_id}/approaches",
    response_model=NeoWsApproachPageResponse,
)
def list_neows_object_approaches(
    neo_reference_id: str,
    limit: int = Query(default=8, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    total = fetch_scalar_with_params(
        db,
        """
        SELECT COUNT(*)
        FROM stg_neows.neo_feed
        WHERE neo_reference_id = :neo_reference_id
        """,
        {"neo_reference_id": neo_reference_id},
    )
    items = fetch_view_rows_with_params(
        db,
        """
        SELECT
            close_approach_date,
            close_approach_datetime,
            orbiting_body,
            relative_velocity_km_per_hour,
            miss_distance_kilometers,
            estimated_diameter_max_km,
            is_potentially_hazardous_asteroid,
            s_ingested_at
        FROM stg_neows.neo_feed
        WHERE neo_reference_id = :neo_reference_id
        ORDER BY close_approach_date DESC, close_approach_datetime DESC NULLS LAST
        LIMIT :limit OFFSET :offset
        """,
        {"neo_reference_id": neo_reference_id, "limit": limit, "offset": offset},
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def build_neows_local_insight(detail: dict, mode: str, live_payload: dict | None = None) -> dict:
    name = detail["name"]
    neo_reference_id = detail["neo_reference_id"]
    if mode == "risk":
        hazard_phrase = (
            "NASAHub marks the object as potentially hazardous."
            if detail["is_potentially_hazardous_asteroid"]
            else "NASAHub does not currently mark the object as potentially hazardous."
        )
        distance_phrase = (
            f"The closest recorded miss distance in NASAHub is about {detail['min_miss_distance_km']:,.0f} km."
            if detail["min_miss_distance_km"] is not None
            else "NASAHub does not currently have a closest miss distance recorded for this object."
        )
        speed_phrase = (
            f"Its fastest recorded approach speed in NASAHub is about {detail['max_velocity_kph']:,.0f} kph."
            if detail["max_velocity_kph"] is not None
            else "NASAHub does not currently have a maximum approach speed recorded for this object."
        )
        summary = (
            f"{name} ({neo_reference_id}) risk context: {hazard_phrase} "
            f"{distance_phrase} {speed_phrase} "
            "This is descriptive context from curated NASAHub data, not a predictive risk assessment."
        )
        return {
            "neo_reference_id": neo_reference_id,
            "mode": mode,
            "title": "Risk Context",
            "summary": summary,
            "sources": ["nasahub_local"],
        }
    if mode == "comparison":
        if live_payload is None:
            summary = (
                f"{name} ({neo_reference_id}) comparison is unavailable because live NASA enrichment could not be loaded. "
                "NASAHub local detail is still available for trusted historical context."
            )
            return {
                "neo_reference_id": neo_reference_id,
                "mode": mode,
                "title": "Local vs Live Comparison",
                "summary": summary,
                "sources": ["nasahub_local"],
            }
        local_approaches = detail["approach_count"]
        live_latest = live_payload["latest_close_approach_date"] or "n/a"
        summary = (
            f"{name} ({neo_reference_id}) comparison: NASAHub currently holds {local_approaches} recorded close approaches"
            f"{f', most recently on {detail['most_recent_close_approach_date']}' if detail['most_recent_close_approach_date'] else ''}. "
            f"The live NASA NeoWs lookup reports a latest approach date of {live_latest}. "
            "Use NASAHub for stable curated history and the live lookup for the freshest upstream object context."
        )
        return {
            "neo_reference_id": neo_reference_id,
            "mode": mode,
            "title": "Local vs Live Comparison",
            "summary": summary,
            "sources": ["nasahub_local", "nasa_neows_live"],
        }
    summary = (
        f"{name} ({neo_reference_id}) is a NeoWs object tracked in NASAHub. "
        f"NASAHub has {detail['approach_count']} recorded close approach"
        f"{'' if detail['approach_count'] == 1 else 'es'} for this object. "
        f"{'It is currently marked as potentially hazardous. ' if detail['is_potentially_hazardous_asteroid'] else 'It is not currently marked as potentially hazardous. '}"
        f"{f'The most recent recorded approach is {detail['most_recent_close_approach_date']} around {detail['latest_orbiting_body']}. ' if detail['most_recent_close_approach_date'] else 'A recent recorded approach is not available in NASAHub. '}"
        "This overview is grounded in NASAHub’s curated local analytics layer."
    )
    return {
        "neo_reference_id": neo_reference_id,
        "mode": mode,
        "title": "Object Overview",
        "summary": summary,
        "sources": ["nasahub_local"],
    }


@router.get(
    "/neows/object/{neo_reference_id}/insight",
    response_model=NeoWsInsightResponse,
)
def get_neows_object_insight(
    neo_reference_id: str,
    mode: str = Query(default="overview", pattern="^(overview|risk|comparison)$"),
    db: Session = Depends(get_db),
):
    detail = fetch_neows_object_detail_row(db, neo_reference_id)
    if detail is None or detail["neo_reference_id"] is None:
        raise HTTPException(status_code=404, detail="NeoWs object not found")

    live_payload = None
    if mode == "comparison":
        try:
            live_payload = fetch_neows_live_enrichment_payload(neo_reference_id)
        except HTTPException:
            live_payload = None

    return build_neows_local_insight(detail, mode, live_payload)


@router.get("/eonet/event/{event_id}", response_model=EonetEventDetailResponse)
def get_eonet_event_detail(event_id: str, db: Session = Depends(get_db)):
    detail = fetch_eonet_event_detail_row(db, event_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="EONET event not found")
    return detail


@router.get("/eonet/event/{event_id}/insight", response_model=EonetInsightResponse)
def get_eonet_event_insight(
    event_id: str,
    mode: str = Query(default="overview", pattern="^(overview|operations)$"),
    db: Session = Depends(get_db),
):
    detail = fetch_eonet_event_detail_row(db, event_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="EONET event not found")
    return build_eonet_insight(detail, mode)


@router.get("/eonet/category-summary", response_model=list[EonetCategorySummaryResponse])
def list_eonet_category_summary(db: Session = Depends(get_db)):
    return fetch_view_rows(
        db,
        """
        SELECT
            category_id,
            category_title,
            total_events,
            open_events,
            closed_events,
            total_sources,
            latest_geometry_at,
            last_ingested_at
        FROM dmt_generic.v_dmt_eonet_category_summary
        ORDER BY total_events DESC, category_id
        """,
    )


@router.get("/eonet/event-overview", response_model=EonetEventOverviewPageResponse)
def list_eonet_event_overview(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    category_id: str | None = Query(default=None),
    event_status: str | None = Query(default=None, pattern="^(open|closed)$"),
    db: Session = Depends(get_db),
):
    filter_clause = """
        WHERE (CAST(:event_status AS text) IS NULL OR v.event_status = CAST(:event_status AS text))
          AND (
              CAST(:category_id AS text) IS NULL
              OR EXISTS (
                  SELECT 1
                  FROM (
                      SELECT
                          e.event_id,
                          e.categories,
                          ROW_NUMBER() OVER (
                              PARTITION BY e.event_id
                              ORDER BY e.s_ingested_at DESC NULLS LAST, e.id DESC
                          ) AS rn
                      FROM stg_eonet.events e
                  ) latest
                  CROSS JOIN LATERAL jsonb_array_elements(
                      COALESCE(latest.categories, '[]'::jsonb)
                  ) AS cat(value)
                  WHERE latest.rn = 1
                    AND latest.event_id = v.event_id
                    AND cat.value ->> 'id' = CAST(:category_id AS text)
              )
          )
    """
    params = {
        "limit": limit,
        "offset": offset,
        "category_id": category_id,
        "event_status": event_status,
    }

    total = fetch_scalar_with_params(
        db,
        f"""
        SELECT COUNT(*)
        FROM dmt_generic.v_dmt_eonet_event_overview v
        {filter_clause}
        """,
        params,
    )
    items = fetch_view_rows_with_params(
        db,
        f"""
        SELECT
            v.event_id,
            v.title,
            v.description,
            v.link,
            v.event_status,
            v.closed_at,
            v.category_count,
            v.category_titles,
            v.source_count,
            v.geometry_count,
            v.latest_geometry_at,
            v.last_ingested_at
        FROM dmt_generic.v_dmt_eonet_event_overview v
        {filter_clause}
        ORDER BY v.latest_geometry_at DESC NULLS LAST, v.event_id
        LIMIT :limit OFFSET :offset
        """,
        params,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/osdr/dataset-summary", response_model=list[OsdrDatasetSummaryResponse])
def list_osdr_dataset_summary(db: Session = Depends(get_db)):
    return fetch_view_rows(
        db,
        """
        SELECT
            dataset_accession,
            dataset_label,
            title,
            description,
            data_source,
            organism,
            release_date,
            repository_url,
            assay_count,
            sample_count,
            file_count,
            last_ingested_at
        FROM dmt_generic.v_dmt_osdr_dataset_summary
        ORDER BY file_count DESC, sample_count DESC, dataset_accession
        """,
    )


@router.get("/osdr/assay-type-summary", response_model=list[OsdrAssayTypeSummaryResponse])
def list_osdr_assay_type_summary(db: Session = Depends(get_db)):
    return fetch_view_rows(
        db,
        """
        SELECT
            assay_type,
            assay_count,
            distinct_dataset_count,
            distinct_technology_count,
            distinct_platform_count
        FROM dmt_generic.v_dmt_osdr_assay_type_summary
        ORDER BY assay_count DESC, assay_type
        """,
    )


@router.get("/osdr/datasets", response_model=OsdrDatasetCatalogPageResponse)
def list_osdr_datasets(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    data_source: str | None = Query(default=None),
    dataset_accession: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    filter_clause = """
        WHERE (CAST(:data_source AS text) IS NULL OR c.data_source = CAST(:data_source AS text))
          AND (CAST(:dataset_accession AS text) IS NULL OR c.dataset_accession = CAST(:dataset_accession AS text))
    """
    params = {
        "limit": limit,
        "offset": offset,
        "data_source": data_source,
        "dataset_accession": dataset_accession,
    }

    total = fetch_scalar_with_params(
        db,
        f"""
        SELECT COUNT(*)
        FROM dmt_generic.v_dmt_osdr_dataset_catalog c
        {filter_clause}
        """,
        params,
    )
    items = fetch_view_rows_with_params(
        db,
        f"""
        SELECT
            c.dataset_accession,
            c.dataset_label,
            c.title,
            c.description,
            c.data_source,
            c.organism,
            c.release_date,
            c.repository_url,
            c.last_ingested_at
        FROM dmt_generic.v_dmt_osdr_dataset_catalog c
        {filter_clause}
        ORDER BY c.dataset_accession
        LIMIT :limit OFFSET :offset
        """,
        params,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/exoplanet/discovery-yearly-summary",
    response_model=list[ExoplanetDiscoveryYearlySummaryResponse],
)
def list_exoplanet_discovery_yearly_summary(db: Session = Depends(get_db)):
    return fetch_view_rows(
        db,
        """
        SELECT
            disc_year,
            planet_count,
            distinct_host_count,
            avg_distance_pc,
            cumulative_planet_count
        FROM dmt_generic.v_dmt_exoplanet_discovery_yearly_summary
        ORDER BY disc_year DESC
        """,
    )


@router.get(
    "/exoplanet/discovery-method-summary",
    response_model=list[ExoplanetDiscoveryMethodSummaryResponse],
)
def list_exoplanet_discovery_method_summary(db: Session = Depends(get_db)):
    return fetch_view_rows(
        db,
        """
        SELECT
            discovery_method,
            planet_count,
            distinct_host_count,
            first_disc_year,
            last_disc_year,
            avg_distance_pc
        FROM dmt_generic.v_dmt_exoplanet_discovery_method_summary
        ORDER BY planet_count DESC, discovery_method
        """,
    )


@router.get("/exoplanet/catalog", response_model=ExoplanetCatalogPageResponse)
def list_exoplanet_catalog(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    discovery_method: str | None = Query(default=None),
    disc_year: int | None = Query(default=None, ge=1900, le=2100),
    db: Session = Depends(get_db),
):
    filter_clause = """
        WHERE (CAST(:discovery_method AS text) IS NULL OR c.discovery_method = CAST(:discovery_method AS text))
          AND (
              CAST(:disc_year AS integer) IS NULL
              OR c.disc_year = CAST(:disc_year AS integer)
          )
    """
    params = {
        "limit": limit,
        "offset": offset,
        "discovery_method": discovery_method,
        "disc_year": disc_year,
    }

    total = fetch_scalar_with_params(
        db,
        f"""
        SELECT COUNT(*)
        FROM dmt_generic.v_dmt_exoplanet_catalog c
        {filter_clause}
        """,
        params,
    )
    items = fetch_view_rows_with_params(
        db,
        f"""
        SELECT
            c.pl_name,
            c.hostname,
            c.discovery_method,
            c.disc_year,
            c.disc_facility,
            c.sy_dist,
            c.pl_orbper,
            c.pl_rade,
            c.pl_bmasse,
            c.st_teff,
            c.last_ingested_at
        FROM dmt_generic.v_dmt_exoplanet_catalog c
        {filter_clause}
        ORDER BY c.sy_dist NULLS LAST, c.pl_name
        LIMIT :limit OFFSET :offset
        """,
        params,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/exoplanet/planets", response_model=list[ExoplanetPlanetSearchResultResponse])
def search_exoplanet_planets(
    query: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    search_term = (query or "").strip()
    search_pattern = f"%{search_term}%"
    prefix_pattern = f"{search_term}%"
    return fetch_view_rows_with_params(
        db,
        """
        SELECT
            pl_name,
            hostname,
            discovery_method,
            disc_year,
            sy_dist
        FROM dmt_generic.v_dmt_exoplanet_catalog
        WHERE (
            CAST(:query AS text) IS NULL
            OR pl_name ILIKE CAST(:search_pattern AS text)
            OR hostname ILIKE CAST(:search_pattern AS text)
        )
        ORDER BY
            CASE
                WHEN CAST(:query AS text) IS NULL THEN 3
                WHEN pl_name = CAST(:query AS text) THEN 0
                WHEN pl_name ILIKE CAST(:prefix_pattern AS text) THEN 1
                WHEN hostname ILIKE CAST(:prefix_pattern AS text) THEN 2
                ELSE 3
            END,
            sy_dist NULLS LAST,
            pl_name
        LIMIT :limit
        """,
        {
            "query": search_term or None,
            "search_pattern": search_pattern,
            "prefix_pattern": prefix_pattern,
            "limit": limit,
        },
    )


@router.get("/exoplanet/planet/{pl_name}", response_model=ExoplanetPlanetDetailResponse)
def get_exoplanet_planet_detail(pl_name: str, db: Session = Depends(get_db)):
    detail = fetch_exoplanet_planet_detail_row(db, pl_name)
    if detail is None:
        raise HTTPException(status_code=404, detail="Exoplanet not found")
    return detail


@router.get("/exoplanet/planet/{pl_name}/insight", response_model=ExoplanetInsightResponse)
def get_exoplanet_planet_insight(
    pl_name: str,
    mode: str = Query(default="overview", pattern="^(overview|discovery|science)$"),
    db: Session = Depends(get_db),
):
    detail = fetch_exoplanet_planet_detail_row(db, pl_name)
    if detail is None:
        raise HTTPException(status_code=404, detail="Exoplanet not found")
    return build_exoplanet_insight(detail, mode)


@router.post("/ask", response_model=AskNasaHubResponse)
def ask_nasahub(payload: AskNasaHubRequest, db: Session = Depends(get_db)):
    if payload.mode == "entity":
        if payload.source not in {"neows", "eonet", "exoplanet"}:
            raise HTTPException(
                status_code=400,
                detail="Entity mode requires source to be one of neows, eonet, or exoplanet",
            )
        if not payload.entity_id:
            raise HTTPException(status_code=400, detail="Entity mode requires entity_id")

    grounded_sources = ["nasahub_local"]
    live_payload = None
    matched_entities: list[dict] = []
    citations: list[dict] = []
    resolved_source = payload.source or "general"
    context_entity_id = payload.entity_id
    if payload.mode == "general":
        resolved_source, context_payload, grounded_sources, citations, matched_entities = build_general_context(
            payload,
            db,
        )
    elif payload.source == "neows":
        detail = fetch_neows_object_detail_row(db, payload.entity_id)
        if detail is None or detail["neo_reference_id"] is None:
            raise HTTPException(status_code=404, detail="NeoWs object not found")
        context_payload = {
            "detail": detail,
            "insight": build_neows_local_insight(detail, "overview"),
        }
        if payload.include_live_enrichment:
            try:
                live_payload = fetch_neows_live_enrichment_payload(payload.entity_id)
                context_payload["live_enrichment"] = live_payload
                grounded_sources.append("nasa_neows_live")
            except HTTPException:
                context_payload["live_enrichment"] = None
        citations = build_ask_citations(
            source=payload.source,
            entity_id=payload.entity_id,
            include_live_enrichment=payload.include_live_enrichment,
            live_payload=live_payload,
        )
        matched_entities = [
            AskNasaHubMatch(
                source="neows",
                entity_id=payload.entity_id,
                title=detail["name"],
                path=f"/analytics/neows/object/{payload.entity_id}",
                note="Exact NeoWs object selected for entity-grounded retrieval.",
            ).model_dump()
        ]
    elif payload.source == "eonet":
        detail = fetch_eonet_event_detail_row(db, payload.entity_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="EONET event not found")
        context_payload = {
            "detail": detail,
            "insight": build_eonet_insight(detail, "overview"),
        }
        citations = build_ask_citations(
            source=payload.source,
            entity_id=payload.entity_id,
            include_live_enrichment=payload.include_live_enrichment,
            live_payload=live_payload,
        )
        matched_entities = [
            AskNasaHubMatch(
                source="eonet",
                entity_id=payload.entity_id,
                title=detail["title"],
                path=f"/analytics/eonet/event/{payload.entity_id}",
                note="Exact EONET event selected for entity-grounded retrieval.",
            ).model_dump()
        ]
    else:
        detail = fetch_exoplanet_planet_detail_row(db, payload.entity_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Exoplanet not found")
        context_payload = {
            "detail": detail,
            "insight": build_exoplanet_insight(detail, "overview"),
        }
        citations = build_ask_citations(
            source=payload.source,
            entity_id=payload.entity_id,
            include_live_enrichment=payload.include_live_enrichment,
            live_payload=live_payload,
        )
        matched_entities = [
            AskNasaHubMatch(
                source="exoplanet",
                entity_id=payload.entity_id,
                title=detail["pl_name"],
                path=f"/analytics/exoplanet/planet/{requests.utils.quote(payload.entity_id, safe='')}",
                note="Exact exoplanet selected for entity-grounded retrieval.",
            ).model_dump()
        ]

    answer = call_openai_grounded_answer(
        source=resolved_source,
        entity_id=context_entity_id or resolved_source,
        question=payload.question,
        context_payload=context_payload,
        chat_history=trim_chat_history(payload.history),
    )
    conversation = trim_chat_history(payload.history)
    conversation.extend(
        [
            {"role": "user", "content": payload.question},
            {"role": "assistant", "content": answer},
        ]
    )
    return {
        "mode": payload.mode,
        "source": resolved_source,
        "entity_id": context_entity_id,
        "question": payload.question,
        "model": OPENAI_MODEL,
        "answer": answer,
        "grounded_sources": grounded_sources,
        "citations": citations,
        "conversation": conversation,
        "matched_entities": matched_entities,
    }
