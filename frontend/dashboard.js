const tokenInput = document.querySelector("#api-token");
const refreshButton = document.querySelector("#refresh-all");
const lastRefresh = document.querySelector("#last-refresh");

const state = {
  token: localStorage.getItem("nasahub_api_token") || "",
};

tokenInput.value = state.token;

tokenInput.addEventListener("change", () => {
  state.token = tokenInput.value.trim();
  if (state.token) {
    localStorage.setItem("nasahub_api_token", state.token);
  } else {
    localStorage.removeItem("nasahub_api_token");
  }
});

refreshButton.addEventListener("click", () => {
  loadDashboard();
});

document.querySelector('[data-action="load-eonet"]').addEventListener("click", loadEonetExplorer);
document.querySelector('[data-action="load-exoplanet"]').addEventListener("click", loadExoplanetExplorer);
document.querySelector('[data-action="load-osdr"]').addEventListener("click", loadOsdrExplorer);

function requestHeaders() {
  if (!state.token) {
    return {};
  }
  return {
    "X-API-Key": state.token,
  };
}

async function fetchJson(path) {
  const response = await fetch(path, {
    headers: requestHeaders(),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }

  return response.json();
}

function setLoading(targetId) {
  document.querySelector(`#${targetId}`).innerHTML = `<div class="loading">Loading...</div>`;
}

function renderError(targetId, message) {
  document.querySelector(
    `#${targetId}`
  ).innerHTML = `<div class="error-box">${escapeHtml(message)}</div>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatNumber(value, digits = 0) {
  if (value === null || value === undefined || value === "") {
    return "n/a";
  }
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: digits,
  });
}

function formatDate(value) {
  if (!value) {
    return "n/a";
  }
  return new Date(value).toLocaleString();
}

function renderTable(targetId, columns, rows) {
  const headers = columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("");
  const body = rows
    .map(
      (row) =>
        `<tr>${columns
          .map((column) => `<td>${column.render ? column.render(row) : escapeHtml(row[column.key] ?? "n/a")}</td>`)
          .join("")}</tr>`
    )
    .join("");

  document.querySelector(`#${targetId}`).innerHTML = `
    <table>
      <thead><tr>${headers}</tr></thead>
      <tbody>${body || `<tr><td colspan="${columns.length}">No data</td></tr>`}</tbody>
    </table>
  `;
}

function renderOverviewCards({ ready, catalog, ingestion }) {
  const degradedRuns = ingestion.filter((row) => row.latest_status !== "success").length;
  const sources = new Set(catalog.endpoints.map((item) => item.source)).size;
  const cards = [
    {
      label: "API readiness",
      value: ready.status,
      sub: ready.database === "ok" ? "Database reachable" : "Database not ready",
    },
    {
      label: "Analytics endpoints",
      value: catalog.endpoints.length,
      sub: "Consumer-discoverable via catalog",
    },
    {
      label: "Sources covered",
      value: sources,
      sub: "tech, NeoWs, EONET, Exoplanet, OSDR",
    },
    {
      label: "Runs needing attention",
      value: degradedRuns,
      sub: degradedRuns === 0 ? "All latest runs are healthy" : "Review ingestion status table",
    },
  ];

  document.querySelector("#overview-cards").innerHTML = cards
    .map(
      (card) => `
        <article class="metric-card">
          <div class="metric-card__label">${escapeHtml(card.label)}</div>
          <div class="metric-card__value">${escapeHtml(card.value)}</div>
          <div class="metric-card__sub">${escapeHtml(card.sub)}</div>
        </article>
      `
    )
    .join("");
}

function renderNeowsSummary(dailySummary, kpis) {
  const latestDay = dailySummary[0];
  const kpiCards = kpis
    .slice(0, 6)
    .map(
      (item) => `
        <article class="kpi-card">
          <div class="kpi-card__label">${escapeHtml(item.category)}</div>
          <div class="kpi-card__value">${escapeHtml(item.object_name || item.object_id)}</div>
          <div class="metric-card__sub">Value: ${formatNumber(item.value, 2)}</div>
        </article>
      `
    )
    .join("");

  document.querySelector("#neows-summary").innerHTML = `
    <div class="metric-grid">
      <article class="metric-card">
        <div class="metric-card__label">Latest close approach day</div>
        <div class="metric-card__value">${escapeHtml(latestDay?.close_approach_date ?? "n/a")}</div>
        <div class="metric-card__sub">${formatNumber(latestDay?.neo_count)} objects, ${formatNumber(latestDay?.hazardous_count)} hazardous</div>
      </article>
      <article class="metric-card">
        <div class="metric-card__label">Avg velocity</div>
        <div class="metric-card__value">${formatNumber(latestDay?.avg_velocity_km_per_hour, 0)}</div>
        <div class="metric-card__sub">km/h on latest day</div>
      </article>
    </div>
    <div class="kpi-grid">${kpiCards}</div>
  `;
}

function renderBarList(targetId, rows, labelKey, valueKey) {
  const maxValue = Math.max(...rows.map((row) => Number(row[valueKey] || 0)), 1);
  document.querySelector(`#${targetId}`).innerHTML = `
    <div class="bar-list">
      ${rows
        .map((row) => {
          const value = Number(row[valueKey] || 0);
          const width = (value / maxValue) * 100;
          return `
            <div class="bar-row">
              <div class="bar-row__meta">
                <span>${escapeHtml(row[labelKey])}</span>
                <strong>${formatNumber(value)}</strong>
              </div>
              <div class="bar"><div class="bar__fill" style="width:${width}%"></div></div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

async function loadSection(targetIds, loader) {
  targetIds.forEach(setLoading);
  try {
    await loader();
    return true;
  } catch (error) {
    targetIds.forEach((targetId) => renderError(targetId, error.message));
    return false;
  }
}

async function loadDashboard() {
  const sectionResults = await Promise.all([
    loadSection(["overview-cards", "ingestion-status-table"], async () => {
      const [ready, catalog, ingestion] = await Promise.all([
        fetchJson("/health/ready"),
        fetchJson("/analytics/catalog"),
        fetchJson("/analytics/ingestion-status"),
      ]);
      renderOverviewCards({ ready, catalog, ingestion });
      renderTable(
        "ingestion-status-table",
        [
          { key: "source_name", label: "Source" },
          { key: "source_endpoint", label: "Endpoint" },
          {
            key: "latest_status",
            label: "Status",
            render: (row) =>
              `<span class="status-pill${row.latest_status === "success" ? "" : " status-pill--warn"}">${escapeHtml(row.latest_status)}</span>`,
          },
          {
            key: "latest_records_inserted",
            label: "Records",
            render: (row) => formatNumber(row.latest_records_inserted),
          },
          {
            key: "latest_run_finished_at",
            label: "Finished",
            render: (row) => escapeHtml(formatDate(row.latest_run_finished_at)),
          },
        ],
        ingestion
      );
    }),
    loadSection(["neows-summary"], async () => {
      const [neowsDaily, neowsKpis] = await Promise.all([
        fetchJson("/analytics/neows/daily-summary"),
        fetchJson("/analytics/neows/kpis"),
      ]);
      renderNeowsSummary(neowsDaily, neowsKpis);
    }),
    loadSection(["eonet-summary", "eonet-explorer"], async () => {
      const [eonetCategory, eonetEvents] = await Promise.all([
        fetchJson("/analytics/eonet/category-summary"),
        fetchJson("/analytics/eonet/event-overview?limit=8&offset=0"),
      ]);
      document.querySelector("#eonet-summary").innerHTML = `
        <div id="eonet-bars"></div>
        <div id="eonet-events-table" class="table-wrap"></div>
      `;
      renderBarList("eonet-bars", eonetCategory.slice(0, 6), "category_title", "total_events");
      renderTable(
        "eonet-events-table",
        [
          { key: "event_id", label: "Event" },
          { key: "category_titles", label: "Categories" },
          { key: "event_status", label: "Status" },
          { key: "latest_geometry_at", label: "Latest activity", render: (row) => escapeHtml(formatDate(row.latest_geometry_at)) },
        ],
        eonetEvents.items
      );
      renderTable(
        "eonet-explorer",
        [
          { key: "event_id", label: "Event" },
          { key: "category_titles", label: "Categories" },
          { key: "event_status", label: "Status" },
        ],
        eonetEvents.items
      );
    }),
    loadSection(["exoplanet-summary", "exoplanet-explorer"], async () => {
      const [exoplanetMethods, exoplanetYears, exoplanetCatalog] = await Promise.all([
        fetchJson("/analytics/exoplanet/discovery-method-summary"),
        fetchJson("/analytics/exoplanet/discovery-yearly-summary"),
        fetchJson("/analytics/exoplanet/catalog?limit=8&offset=0"),
      ]);
      document.querySelector("#exoplanet-summary").innerHTML = `
        <div id="exo-method-bars"></div>
        <div id="exo-table" class="table-wrap"></div>
      `;
      renderBarList("exo-method-bars", exoplanetMethods.slice(0, 6), "discovery_method", "planet_count");
      renderTable(
        "exo-table",
        [
          { key: "pl_name", label: "Planet" },
          { key: "discovery_method", label: "Method" },
          { key: "disc_year", label: "Year" },
          { key: "sy_dist", label: "Distance (pc)", render: (row) => formatNumber(row.sy_dist, 2) },
        ],
        exoplanetCatalog.items
      );
      renderTable(
        "exoplanet-explorer",
        [
          { key: "pl_name", label: "Planet" },
          { key: "discovery_method", label: "Method" },
          { key: "disc_year", label: "Year" },
        ],
        exoplanetCatalog.items
      );
    }),
    loadSection(["osdr-summary", "osdr-explorer"], async () => {
      const [osdrSummary, osdrAssays, osdrDatasets] = await Promise.all([
        fetchJson("/analytics/osdr/dataset-summary"),
        fetchJson("/analytics/osdr/assay-type-summary"),
        fetchJson("/analytics/osdr/datasets?limit=8&offset=0"),
      ]);
      document.querySelector("#osdr-summary").innerHTML = `
        <div id="osdr-dataset-table" class="table-wrap"></div>
        <div id="osdr-assay-bars"></div>
      `;
      renderTable(
        "osdr-dataset-table",
        [
          { key: "dataset_accession", label: "Dataset" },
          { key: "assay_count", label: "Assays", render: (row) => formatNumber(row.assay_count) },
          { key: "sample_count", label: "Samples", render: (row) => formatNumber(row.sample_count) },
          { key: "file_count", label: "Files", render: (row) => formatNumber(row.file_count) },
        ],
        osdrSummary.slice(0, 8)
      );
      renderBarList("osdr-assay-bars", osdrAssays.slice(0, 6), "assay_type", "assay_count");
      renderTable(
        "osdr-explorer",
        [
          { key: "dataset_accession", label: "Dataset" },
          { key: "dataset_label", label: "Label" },
          { key: "last_ingested_at", label: "Ingested", render: (row) => escapeHtml(formatDate(row.last_ingested_at)) },
        ],
        osdrDatasets.items
      );
    }),
  ]);

  lastRefresh.textContent = sectionResults.every(Boolean)
    ? `Last refreshed ${new Date().toLocaleString()}`
    : `Partially refreshed ${new Date().toLocaleString()}`;
}

async function loadEonetExplorer() {
  setLoading("eonet-explorer");
  try {
    const category = document.querySelector("#eonet-category").value.trim();
    const status = document.querySelector("#eonet-status").value;
    const params = new URLSearchParams({ limit: "12", offset: "0" });
    if (category) params.set("category_id", category);
    if (status) params.set("event_status", status);
    const payload = await fetchJson(`/analytics/eonet/event-overview?${params.toString()}`);
    renderTable(
      "eonet-explorer",
      [
        { key: "event_id", label: "Event" },
        { key: "category_titles", label: "Categories" },
        { key: "event_status", label: "Status" },
        { key: "latest_geometry_at", label: "Latest activity", render: (row) => escapeHtml(formatDate(row.latest_geometry_at)) },
      ],
      payload.items
    );
  } catch (error) {
    renderError("eonet-explorer", error.message);
  }
}

async function loadExoplanetExplorer() {
  setLoading("exoplanet-explorer");
  try {
    const method = document.querySelector("#exoplanet-method").value.trim();
    const year = document.querySelector("#exoplanet-year").value.trim();
    const params = new URLSearchParams({ limit: "12", offset: "0" });
    if (method) params.set("discovery_method", method);
    if (year) params.set("disc_year", year);
    const payload = await fetchJson(`/analytics/exoplanet/catalog?${params.toString()}`);
    renderTable(
      "exoplanet-explorer",
      [
        { key: "pl_name", label: "Planet" },
        { key: "discovery_method", label: "Method" },
        { key: "disc_year", label: "Year" },
        { key: "sy_dist", label: "Distance (pc)", render: (row) => formatNumber(row.sy_dist, 2) },
      ],
      payload.items
    );
  } catch (error) {
    renderError("exoplanet-explorer", error.message);
  }
}

async function loadOsdrExplorer() {
  setLoading("osdr-explorer");
  try {
    const accession = document.querySelector("#osdr-accession").value.trim();
    const source = document.querySelector("#osdr-source").value.trim();
    const params = new URLSearchParams({ limit: "12", offset: "0" });
    if (accession) params.set("dataset_accession", accession);
    if (source) params.set("data_source", source);
    const payload = await fetchJson(`/analytics/osdr/datasets?${params.toString()}`);
    renderTable(
      "osdr-explorer",
      [
        { key: "dataset_accession", label: "Dataset" },
        { key: "dataset_label", label: "Label" },
        { key: "last_ingested_at", label: "Ingested", render: (row) => escapeHtml(formatDate(row.last_ingested_at)) },
      ],
      payload.items
    );
  } catch (error) {
    renderError("osdr-explorer", error.message);
  }
}

loadDashboard();
