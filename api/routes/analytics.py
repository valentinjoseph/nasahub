from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.schemas import (
    AnalyticsCatalogResponse,
    AnalyticsEndpointInfoResponse,
    EonetCategorySummaryResponse,
    EonetEventOverviewPageResponse,
    EonetEventOverviewResponse,
    ExoplanetCatalogPageResponse,
    ExoplanetDiscoveryMethodSummaryResponse,
    ExoplanetDiscoveryYearlySummaryResponse,
    IngestionStatusResponse,
    NeoWsDailySummaryResponse,
    NeoWsKpiResponse,
    OsdrAssayTypeSummaryResponse,
    OsdrDatasetCatalogPageResponse,
    OsdrDatasetSummaryResponse,
)
from db.deps import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])

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
