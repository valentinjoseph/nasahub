from datetime import date, datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database: str


class AnalyticsEndpointInfoResponse(BaseModel):
    path: str
    source: str
    summary: str
    paginated: bool
    filters: list[str]


class AnalyticsCatalogResponse(BaseModel):
    endpoints: list[AnalyticsEndpointInfoResponse]


class IngestionStatusResponse(BaseModel):
    source_name: str
    source_endpoint: str
    latest_run_started_at: datetime
    latest_run_finished_at: datetime | None
    latest_status: str
    latest_records_inserted: int
    created_at: datetime


class MonitorCategoryStatusResponse(BaseModel):
    issue_count: int
    issues: list[str]


class MonitorStatusResponse(BaseModel):
    checked_at_utc: datetime | None
    overall_status: str
    issue_count: int
    source: str
    categories: dict[str, MonitorCategoryStatusResponse]


class NeoWsDailySummaryResponse(BaseModel):
    close_approach_date: date
    neo_count: int
    hazardous_count: int
    distinct_object_count: int
    avg_velocity_km_per_hour: float | None
    min_miss_distance_kilometers: float | None
    max_miss_distance_kilometers: float | None
    biggest_estimated_diameter_max_km: float | None


class NeoWsKpiResponse(BaseModel):
    category: str
    object_id: str
    object_name: str
    est_max_diameter_m: float | None
    velocity_kph: float | None
    recent_approach_date: date | None
    is_hazardous_flag: bool | None
    miss_distance_km: float | None
    value: float | None


class NeoWsObjectDetailResponse(BaseModel):
    neo_reference_id: str
    name: str
    nasa_jpl_url: str | None
    absolute_magnitude_h: float | None
    is_potentially_hazardous_asteroid: bool | None
    is_sentry_object: bool | None
    estimated_diameter_min_km: float | None
    estimated_diameter_max_km: float | None
    first_close_approach_date: date | None
    most_recent_close_approach_date: date | None
    approach_count: int
    min_miss_distance_km: float | None
    max_velocity_kph: float | None
    latest_orbiting_body: str | None
    last_ingested_at: datetime | None


class NeoWsObjectSearchResultResponse(BaseModel):
    neo_reference_id: str
    name: str
    is_potentially_hazardous_asteroid: bool | None
    most_recent_close_approach_date: date | None
    approach_count: int


class NeoWsLiveEnrichmentResponse(BaseModel):
    neo_reference_id: str
    name: str
    source: str
    source_url: str
    generated_summary: str
    nasa_jpl_url: str | None
    absolute_magnitude_h: float | None
    is_potentially_hazardous_asteroid: bool | None
    estimated_diameter_min_km: float | None
    estimated_diameter_max_km: float | None
    latest_close_approach_date: date | None
    latest_orbiting_body: str | None
    latest_relative_velocity_kph: float | None
    latest_miss_distance_km: float | None


class NeoWsApproachItemResponse(BaseModel):
    close_approach_date: date
    close_approach_datetime: datetime | None
    orbiting_body: str
    relative_velocity_km_per_hour: float | None
    miss_distance_kilometers: float | None
    estimated_diameter_max_km: float | None
    is_potentially_hazardous_asteroid: bool | None
    s_ingested_at: datetime


class NeoWsApproachPageResponse(BaseModel):
    items: list[NeoWsApproachItemResponse]
    total: int
    limit: int
    offset: int


class NeoWsInsightResponse(BaseModel):
    neo_reference_id: str
    mode: str
    title: str
    summary: str
    sources: list[str]


class EonetEventDetailResponse(BaseModel):
    event_id: str
    title: str
    description: str | None
    link: str | None
    event_status: str
    closed_at: datetime | None
    category_count: int
    category_titles: str | None
    source_count: int
    source_titles: str | None
    geometry_count: int
    latest_geometry_at: datetime | None
    last_ingested_at: datetime


class EonetInsightResponse(BaseModel):
    event_id: str
    mode: str
    title: str
    summary: str
    sources: list[str]


class EonetCategorySummaryResponse(BaseModel):
    category_id: str
    category_title: str
    total_events: int
    open_events: int
    closed_events: int
    total_sources: int
    latest_geometry_at: datetime | None
    last_ingested_at: datetime


class EonetEventOverviewResponse(BaseModel):
    event_id: str
    title: str
    description: str | None
    link: str | None
    event_status: str
    closed_at: datetime | None
    category_count: int
    category_titles: str | None
    source_count: int
    geometry_count: int
    latest_geometry_at: datetime | None
    last_ingested_at: datetime


class EonetEventOverviewPageResponse(BaseModel):
    items: list[EonetEventOverviewResponse]
    total: int
    limit: int
    offset: int


class ExoplanetDiscoveryYearlySummaryResponse(BaseModel):
    disc_year: int
    planet_count: int
    distinct_host_count: int
    avg_distance_pc: float | None
    cumulative_planet_count: int


class ExoplanetDiscoveryMethodSummaryResponse(BaseModel):
    discovery_method: str
    planet_count: int
    distinct_host_count: int
    first_disc_year: int | None
    last_disc_year: int | None
    avg_distance_pc: float | None


class ExoplanetCatalogItemResponse(BaseModel):
    pl_name: str
    hostname: str | None
    discovery_method: str
    disc_year: int | None
    disc_facility: str | None
    sy_dist: float | None
    pl_orbper: float | None
    pl_rade: float | None
    pl_bmasse: float | None
    st_teff: float | None
    last_ingested_at: datetime


class ExoplanetCatalogPageResponse(BaseModel):
    items: list[ExoplanetCatalogItemResponse]
    total: int
    limit: int
    offset: int


class ExoplanetPlanetDetailResponse(BaseModel):
    pl_name: str
    hostname: str | None
    discovery_method: str
    disc_year: int | None
    disc_facility: str | None
    sy_dist: float | None
    pl_orbper: float | None
    pl_rade: float | None
    pl_bmasse: float | None
    st_teff: float | None
    last_ingested_at: datetime


class ExoplanetPlanetSearchResultResponse(BaseModel):
    pl_name: str
    hostname: str | None
    discovery_method: str
    disc_year: int | None
    sy_dist: float | None


class ExoplanetInsightResponse(BaseModel):
    pl_name: str
    mode: str
    title: str
    summary: str
    sources: list[str]


class OsdrDatasetSummaryResponse(BaseModel):
    dataset_accession: str
    dataset_label: str
    title: str | None
    description: str | None
    data_source: str | None
    organism: str | None
    release_date: date | None
    repository_url: str | None
    assay_count: int
    sample_count: int
    file_count: int
    last_ingested_at: datetime


class OsdrAssayTypeSummaryResponse(BaseModel):
    assay_type: str
    assay_count: int
    distinct_dataset_count: int
    distinct_technology_count: int
    distinct_platform_count: int


class OsdrDatasetCatalogItemResponse(BaseModel):
    dataset_accession: str
    dataset_label: str
    title: str | None
    description: str | None
    data_source: str | None
    organism: str | None
    release_date: date | None
    repository_url: str | None
    last_ingested_at: datetime


class OsdrDatasetCatalogPageResponse(BaseModel):
    items: list[OsdrDatasetCatalogItemResponse]
    total: int
    limit: int
    offset: int


class SavedAskContextRequest(BaseModel):
    label: str
    mode: str = Field(default="entity", pattern="^(entity|general)$")
    source: str = Field(default="general", pattern="^(general|neows|eonet|exoplanet|osdr)$")
    entity_id: str | None = None
    comparison_entity_id: str | None = None
    question: str = ""
    include_live_enrichment: bool = False


class SavedAskContextResponse(BaseModel):
    context_id: str
    label: str
    mode: str
    source: str
    entity_id: str | None
    comparison_entity_id: str | None
    question: str
    include_live_enrichment: bool
    created_at: datetime
    updated_at: datetime


class PinnedEntityRequest(BaseModel):
    source: str = Field(pattern="^(neows|eonet|exoplanet|osdr)$")
    entity_id: str
    label: str
    watchlist: bool = False


class PinnedEntityResponse(BaseModel):
    pin_id: str
    source: str
    entity_id: str
    label: str
    watchlist: bool
    created_at: datetime
    updated_at: datetime


class AskNasaHubRequest(BaseModel):
    mode: str = Field(default="entity", pattern="^(entity|general)$")
    source: str | None = Field(default=None, pattern="^(general|neows|eonet|exoplanet)$")
    entity_id: str | None = None
    comparison_entity_id: str | None = None
    question: str
    include_live_enrichment: bool = False
    history: list["AskNasaHubMessage"] = Field(default_factory=list)


class AskNasaHubMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class AskNasaHubCitation(BaseModel):
    source: str
    title: str
    entity_id: str | None
    path: str | None
    source_url: str | None
    note: str | None


class AskNasaHubMatch(BaseModel):
    source: str
    entity_id: str
    title: str
    path: str | None
    note: str | None
    rank_reason: str | None = None
    metric_label: str | None = None
    metric_value: str | None = None


class AskNasaHubResponse(BaseModel):
    mode: str
    source: str
    entity_id: str | None
    comparison_entity_id: str | None = None
    question: str
    model: str
    answer: str
    grounded_sources: list[str]
    citations: list[AskNasaHubCitation]
    conversation: list[AskNasaHubMessage]
    matched_entities: list[AskNasaHubMatch]
