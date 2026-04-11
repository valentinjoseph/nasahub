const tokenInput = document.querySelector("#api-token");
const refreshButton = document.querySelector("#refresh-all");
const lastRefresh = document.querySelector("#last-refresh");
const apiModeIndicator = document.querySelector("#api-mode-indicator");
const askModeSelect = document.querySelector("#ask-mode");
const askSourceSelect = document.querySelector("#ask-source");
const askEntityInput = document.querySelector("#ask-entity-id");

const state = {
  token: localStorage.getItem("nasahub_api_token") || "",
  askHistory: JSON.parse(localStorage.getItem("nasahub_ask_history") || "[]"),
  view: "all",
  neowsApproaches: {
    limit: 6,
    offset: 0,
    total: 0,
    currentObjectId: "",
  },
  explorers: {
    eonet: { limit: 8, offset: 0, total: 0 },
    exoplanet: { limit: 8, offset: 0, total: 0 },
    osdr: { limit: 8, offset: 0, total: 0 },
  },
};

tokenInput.value = state.token;
updateApiModeIndicator();

tokenInput.addEventListener("change", () => {
  state.token = tokenInput.value.trim();
  if (state.token) {
    localStorage.setItem("nasahub_api_token", state.token);
  } else {
    localStorage.removeItem("nasahub_api_token");
  }
  updateApiModeIndicator();
});

refreshButton.addEventListener("click", () => {
  loadDashboard();
});

document.querySelector('[data-action="load-eonet"]').addEventListener("click", loadEonetExplorer);
document.querySelector('[data-action="load-exoplanet"]').addEventListener("click", loadExoplanetExplorer);
document.querySelector('[data-action="load-osdr"]').addEventListener("click", loadOsdrExplorer);
document.querySelector("#load-eonet-detail").addEventListener("click", () => {
  loadEonetDetail(document.querySelector("#eonet-event-id").value.trim());
});
document.querySelector("#eonet-insight-overview").addEventListener("click", () => {
  loadEonetInsight(document.querySelector("#eonet-event-id").value.trim(), "overview");
});
document.querySelector("#eonet-insight-operations").addEventListener("click", () => {
  loadEonetInsight(document.querySelector("#eonet-event-id").value.trim(), "operations");
});
document.querySelector("#find-exoplanet-planet").addEventListener("click", loadExoplanetPlanetFinder);
document.querySelector("#exoplanet-planet-results").addEventListener("change", (event) => {
  const plName = event.target.value;
  document.querySelector("#exoplanet-planet-name").value = plName;
  if (plName) {
    loadExoplanetDetail(plName);
  }
});
document.querySelector("#load-exoplanet-detail").addEventListener("click", () => {
  loadExoplanetDetail(document.querySelector("#exoplanet-planet-name").value.trim());
});
document.querySelector("#exoplanet-insight-overview").addEventListener("click", () => {
  loadExoplanetInsight(document.querySelector("#exoplanet-planet-name").value.trim(), "overview");
});
document.querySelector("#exoplanet-insight-discovery").addEventListener("click", () => {
  loadExoplanetInsight(document.querySelector("#exoplanet-planet-name").value.trim(), "discovery");
});
document.querySelector("#exoplanet-insight-science").addEventListener("click", () => {
  loadExoplanetInsight(document.querySelector("#exoplanet-planet-name").value.trim(), "science");
});
document.querySelector("#find-neows-object").addEventListener("click", loadNeowsObjectFinder);
document.querySelector("#load-neows-object").addEventListener("click", () => {
  loadNeowsObjectDetail(document.querySelector("#neows-object-id").value.trim());
});
document.querySelector("#enrich-neows-object").addEventListener("click", () => {
  loadNeowsLiveEnrichment(document.querySelector("#neows-object-id").value.trim());
});
document.querySelector("#neows-insight-overview").addEventListener("click", () => {
  loadNeowsInsight(document.querySelector("#neows-object-id").value.trim(), "overview");
});
document.querySelector("#neows-insight-risk").addEventListener("click", () => {
  loadNeowsInsight(document.querySelector("#neows-object-id").value.trim(), "risk");
});
document.querySelector("#neows-insight-compare").addEventListener("click", () => {
  loadNeowsInsight(document.querySelector("#neows-object-id").value.trim(), "comparison");
});
document.querySelector("#neows-object-results").addEventListener("change", (event) => {
  const neoReferenceId = event.target.value;
  document.querySelector("#neows-object-id").value = neoReferenceId;
  if (neoReferenceId) {
    loadNeowsObjectDetail(neoReferenceId);
  }
});
document.querySelector("#neows-approach-prev").addEventListener("click", () => changeNeowsApproachPage(-1));
document.querySelector("#neows-approach-next").addEventListener("click", () => changeNeowsApproachPage(1));
document.querySelector("#eonet-prev").addEventListener("click", () => changeExplorerPage("eonet", -1));
document.querySelector("#eonet-next").addEventListener("click", () => changeExplorerPage("eonet", 1));
document.querySelector("#exoplanet-prev").addEventListener("click", () => changeExplorerPage("exoplanet", -1));
document.querySelector("#exoplanet-next").addEventListener("click", () => changeExplorerPage("exoplanet", 1));
document.querySelector("#osdr-prev").addEventListener("click", () => changeExplorerPage("osdr", -1));
document.querySelector("#osdr-next").addEventListener("click", () => changeExplorerPage("osdr", 1));
document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => {
    setDashboardView(button.dataset.view);
  });
});
document.querySelector("#ask-nasahub").addEventListener("click", loadAskNasaHub);
document.querySelector("#clear-ask-history").addEventListener("click", clearAskHistory);
askModeSelect.addEventListener("change", updateAskModeState);

renderAskHistory();
updateAskModeState();

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

function updateApiModeIndicator() {
  if (state.token) {
    apiModeIndicator.className = "section-badge section-badge--ok";
    apiModeIndicator.textContent = "Token mode active";
    return;
  }
  apiModeIndicator.className = "section-badge section-badge--loading";
  apiModeIndicator.textContent = "Guest mode";
}

function persistAskHistory() {
  localStorage.setItem("nasahub_ask_history", JSON.stringify(state.askHistory.slice(-8)));
}

function clearAskHistory() {
  state.askHistory = [];
  localStorage.removeItem("nasahub_ask_history");
  renderAskHistory();
  document.querySelector("#ask-nasahub-response").textContent =
    "Conversation cleared. Ask a new grounded question when you are ready.";
}

function updateAskModeState() {
  const isGeneral = askModeSelect.value === "general";
  askEntityInput.disabled = isGeneral;
  askEntityInput.placeholder = isGeneral ? "optional in general mode" : "entity id or object name";
  if (isGeneral && !askSourceSelect.value) {
    askSourceSelect.value = "general";
  }
  if (!isGeneral && askSourceSelect.value === "general") {
    askSourceSelect.value = "neows";
  }
}

function setDashboardView(view) {
  state.view = view;
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("tab-button--active", button.dataset.view === view);
  });
  document.querySelectorAll("[data-panel-group]").forEach((panel) => {
    panel.hidden = !(view === "all" || panel.dataset.panelGroup === view);
  });
}

function setSectionStatus(section, tone, label) {
  const badge = document.querySelector(`#status-${section}`);
  if (!badge) {
    return;
  }
  badge.className = `section-badge section-badge--${tone}`;
  badge.textContent = label;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderAskHistory() {
  const target = document.querySelector("#ask-nasahub-history");
  if (!state.askHistory.length) {
    target.textContent = "Conversation history will appear here once you ask a question.";
    return;
  }
  target.innerHTML = state.askHistory
    .map(
      (message) => `
        <article class="chat-message chat-message--${escapeHtml(message.role)}">
          <span class="chat-message__role">${escapeHtml(message.role)}</span>
          <div>${escapeHtml(message.content)}</div>
        </article>
      `
    )
    .join("");
}

function renderCitations(citations) {
  if (!citations || !citations.length) {
    return `<div class="muted">No citations were returned for this response.</div>`;
  }
  return `
    <div class="citation-list">
      ${citations
        .map(
          (citation) => `
            <article class="citation-item">
              <strong>${escapeHtml(citation.title)}</strong>
              <div><span class="muted">Source:</span> ${escapeHtml(citation.source)}</div>
              <div><span class="muted">Entity:</span> ${escapeHtml(citation.entity_id ?? "n/a")}</div>
              <div><span class="muted">Path:</span> ${escapeHtml(citation.path ?? "n/a")}</div>
              <div><span class="muted">Source URL:</span> ${escapeHtml(citation.source_url ?? "n/a")}</div>
              <div><span class="muted">Note:</span> ${escapeHtml(citation.note ?? "n/a")}</div>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function renderMatchedEntities(matches) {
  if (!matches || !matches.length) {
    return `<span class="muted">No specific entity match was required for this answer.</span>`;
  }
  return matches
    .map(
      (match) => `
        <article class="citation-item">
          <strong>${escapeHtml(match.title)}</strong>
          <div><span class="muted">Source:</span> ${escapeHtml(match.source)}</div>
          <div><span class="muted">Entity:</span> ${escapeHtml(match.entity_id)}</div>
          <div><span class="muted">Why this matched:</span> ${escapeHtml(match.rank_reason ?? match.note ?? "n/a")}</div>
          <div><span class="muted">Metric:</span> ${escapeHtml(match.metric_label ?? "n/a")} = ${escapeHtml(match.metric_value ?? "n/a")}</div>
          <div><span class="muted">Path:</span> ${escapeHtml(match.path ?? "n/a")}</div>
        </article>
      `
    )
    .join("");
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

function renderDetailGrid(targetId, fields) {
  document.querySelector(`#${targetId}`).innerHTML = fields
    .map(
      (field) => `
        <article class="detail-card">
          <div class="detail-card__label">${escapeHtml(field.label)}</div>
          <div class="detail-card__value">${field.value}</div>
        </article>
      `
    )
    .join("");
}

function renderExoplanetPlanetOptions(items) {
  const select = document.querySelector("#exoplanet-planet-results");
  const options = items
    .map(
      (item) =>
        `<option value="${escapeHtml(item.pl_name)}">${escapeHtml(item.pl_name)}${item.hostname ? ` | ${escapeHtml(item.hostname)}` : ""}</option>`
    )
    .join("");
  select.innerHTML = `<option value="">Choose a matching planet</option>${options}`;
}

function renderNeowsObjectOptions(items) {
  const select = document.querySelector("#neows-object-results");
  const options = items
    .map(
      (item) =>
        `<option value="${escapeHtml(item.neo_reference_id)}">${escapeHtml(item.name)} [${escapeHtml(item.neo_reference_id)}]</option>`
    )
    .join("");
  select.innerHTML = `<option value="">Choose a matching object</option>${options}`;
}

function renderNeowsApproachMeta(payload) {
  const start = payload.total === 0 ? 0 : payload.offset + 1;
  const end = Math.min(payload.offset + payload.items.length, payload.total);
  document.querySelector("#neows-approach-meta").textContent =
    `${start}-${end} of ${formatNumber(payload.total)} recorded approaches`;
  state.neowsApproaches.total = payload.total;
  document.querySelector("#neows-approach-prev").disabled = payload.offset === 0;
  document.querySelector("#neows-approach-next").disabled =
    payload.offset + payload.items.length >= payload.total;
}

function buildNeowsObjectSummary(payload) {
  const approachPhrase =
    payload.approach_count > 0
      ? `NASAHub has recorded ${formatNumber(payload.approach_count)} close approach${payload.approach_count === 1 ? "" : "es"} for this object`
      : "NASAHub currently has identity-level NeoWs data for this object, but no close-approach history in the curated feed layer";

  const hazardPhrase =
    payload.is_potentially_hazardous_asteroid === true
      ? "It is currently flagged as potentially hazardous."
      : payload.is_potentially_hazardous_asteroid === false
        ? "It is not currently flagged as potentially hazardous."
        : "Its hazard flag is not available in the current curated payload.";

  const sizePhrase =
    payload.estimated_diameter_min_km !== null && payload.estimated_diameter_max_km !== null
      ? `Its estimated diameter ranges from about ${formatNumber(payload.estimated_diameter_min_km, 3)} km to ${formatNumber(payload.estimated_diameter_max_km, 3)} km.`
      : "Its estimated diameter range is not available in the current curated payload.";

  const motionPhrase =
    payload.most_recent_close_approach_date
      ? `The most recent recorded close approach in NASAHub is ${payload.most_recent_close_approach_date}${payload.latest_orbiting_body ? ` around ${payload.latest_orbiting_body}` : ""}.`
      : "A most recent close-approach date is not currently available in NASAHub for this object.";

  const distancePhrase =
    payload.min_miss_distance_km !== null
      ? `The closest recorded miss distance in NASAHub is about ${formatNumber(payload.min_miss_distance_km, 0)} km.`
      : "A closest miss distance is not currently available in NASAHub for this object.";

  return `${payload.name} (${payload.neo_reference_id}) is a NeoWs object tracked in NASAHub. ${approachPhrase}. ${hazardPhrase} ${sizePhrase} ${motionPhrase} ${distancePhrase}`;
}

function renderExplorerMeta(explorerKey, payload, filters = []) {
  const start = payload.total === 0 ? 0 : payload.offset + 1;
  const end = Math.min(payload.offset + payload.items.length, payload.total);
  const filterSummary = filters.filter(Boolean).join(" | ");
  document.querySelector(`#${explorerKey}-explorer-meta`).textContent =
    `${start}-${end} of ${formatNumber(payload.total)} rows${filterSummary ? ` | ${filterSummary}` : ""}`;

  const pageState = state.explorers[explorerKey];
  pageState.total = payload.total;
  document.querySelector(`#${explorerKey}-prev`).disabled = payload.offset === 0;
  document.querySelector(`#${explorerKey}-next`).disabled = payload.offset + payload.items.length >= payload.total;
}

function populateExoplanetMethodOptions(methods) {
  const select = document.querySelector("#exoplanet-method");
  const currentValue = select.value;
  const options = methods
    .map(
      (item) =>
        `<option value="${escapeHtml(item.discovery_method)}">${escapeHtml(item.discovery_method)} (${formatNumber(item.planet_count)})</option>`
    )
    .join("");
  select.innerHTML = `<option value="">Any discovery method</option>${options}`;
  if (currentValue) {
    select.value = currentValue;
  }
}

function populateEonetCategoryOptions(categories) {
  const select = document.querySelector("#eonet-category");
  const currentValue = select.value;
  const options = categories
    .map(
      (item) =>
        `<option value="${escapeHtml(item.category_id)}">${escapeHtml(item.category_title)} (${formatNumber(item.total_events)})</option>`
    )
    .join("");
  select.innerHTML = `<option value="">Any category</option>${options}`;
  if (currentValue) {
    select.value = currentValue;
  }
}

function populateOsdrSourceOptions(datasetSummary) {
  const select = document.querySelector("#osdr-source");
  const currentValue = select.value;
  const uniqueSources = [...new Set(datasetSummary.map((item) => item.data_source).filter(Boolean))].sort();
  const options = uniqueSources
    .map((source) => `<option value="${escapeHtml(source)}">${escapeHtml(source)}</option>`)
    .join("");
  select.innerHTML = `<option value="">Any data source</option>${options}`;
  if (currentValue) {
    select.value = currentValue;
  }
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
          <button class="kpi-card__button" type="button" data-neows-object="${escapeHtml(item.object_id)}">
            <div class="kpi-card__label">${escapeHtml(item.category)}</div>
            <div class="kpi-card__value">${escapeHtml(item.object_name || item.object_id)}</div>
            <div class="metric-card__sub">Value: ${formatNumber(item.value, 2)}</div>
          </button>
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

  document.querySelectorAll("[data-neows-object]").forEach((button) => {
    button.addEventListener("click", () => {
      const neoReferenceId = button.dataset.neowsObject;
      document.querySelector("#neows-object-id").value = neoReferenceId;
      loadNeowsObjectDetail(neoReferenceId);
    });
  });
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
  setSectionStatus("overview", "loading", "Loading");
  setSectionStatus("ingestion", "loading", "Loading");
  setSectionStatus("neows", "loading", "Loading");
  setSectionStatus("eonet", "loading", "Loading");
  setSectionStatus("exoplanet", "loading", "Loading");
  setSectionStatus("osdr", "loading", "Loading");

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
      setSectionStatus("overview", ready.database === "ok" ? "ok" : "warn", ready.database === "ok" ? "Ready" : "Degraded");
      setSectionStatus(
        "ingestion",
        ingestion.some((row) => row.latest_status !== "success") ? "warn" : "ok",
        ingestion.some((row) => row.latest_status !== "success") ? "Attention" : "Healthy"
      );
    }),
    loadSection(["neows-summary"], async () => {
      const [neowsDaily, neowsKpis] = await Promise.all([
        fetchJson("/analytics/neows/daily-summary"),
        fetchJson("/analytics/neows/kpis"),
      ]);
      renderNeowsSummary(neowsDaily, neowsKpis);
      setSectionStatus("neows", "ok", `${formatNumber(neowsKpis.length)} KPIs`);
      await loadNeowsObjectFinder();
      const firstObjectId = neowsKpis[0]?.object_id;
      if (firstObjectId) {
        document.querySelector("#neows-object-id").value = firstObjectId;
        await loadNeowsObjectDetail(firstObjectId);
      }
    }),
    loadSection(["eonet-summary", "eonet-explorer"], async () => {
      const [eonetCategory, eonetEvents] = await Promise.all([
        fetchJson("/analytics/eonet/category-summary"),
        fetchJson("/analytics/eonet/event-overview?limit=8&offset=0"),
      ]);
      populateEonetCategoryOptions(eonetCategory);
      document.querySelector("#eonet-summary").innerHTML = `
        <div id="eonet-bars"></div>
        <div id="eonet-events-table" class="table-wrap"></div>
      `;
      renderBarList("eonet-bars", eonetCategory.slice(0, 6), "category_title", "total_events");
      renderTable(
        "eonet-events-table",
        [
          {
            key: "event_id",
            label: "Event",
            render: (row) =>
              `<button class="button" type="button" data-eonet-event="${escapeHtml(row.event_id)}">${escapeHtml(row.event_id)}</button>`,
          },
          { key: "category_titles", label: "Categories" },
          { key: "event_status", label: "Status" },
          { key: "latest_geometry_at", label: "Latest activity", render: (row) => escapeHtml(formatDate(row.latest_geometry_at)) },
        ],
        eonetEvents.items
      );
      renderTable(
        "eonet-explorer",
        [
          {
            key: "event_id",
            label: "Event",
            render: (row) =>
              `<button class="button" type="button" data-eonet-event="${escapeHtml(row.event_id)}">${escapeHtml(row.event_id)}</button>`,
          },
          { key: "category_titles", label: "Categories" },
          { key: "event_status", label: "Status" },
        ],
        eonetEvents.items
      );
      document.querySelectorAll("[data-eonet-event]").forEach((button) => {
        button.addEventListener("click", () => loadEonetDetail(button.dataset.eonetEvent));
      });
      state.explorers.eonet.offset = 0;
      state.explorers.eonet.limit = 8;
      renderExplorerMeta("eonet", {
        ...eonetEvents,
        offset: 0,
        items: eonetEvents.items.slice(0, eonetEvents.items.length),
      });
      setSectionStatus("eonet", "ok", `${formatNumber(eonetCategory.length)} categories`);
      if (eonetEvents.items[0]?.event_id) {
        document.querySelector("#eonet-event-id").value = eonetEvents.items[0].event_id;
        await loadEonetDetail(eonetEvents.items[0].event_id);
      }
    }),
    loadSection(["exoplanet-summary", "exoplanet-explorer"], async () => {
      const [exoplanetMethods, exoplanetYears, exoplanetCatalog] = await Promise.all([
        fetchJson("/analytics/exoplanet/discovery-method-summary"),
        fetchJson("/analytics/exoplanet/discovery-yearly-summary"),
        fetchJson("/analytics/exoplanet/catalog?limit=8&offset=0"),
      ]);
      populateExoplanetMethodOptions(exoplanetMethods);
      document.querySelector("#exoplanet-summary").innerHTML = `
        <div id="exo-method-bars"></div>
        <div id="exo-table" class="table-wrap"></div>
      `;
      renderBarList("exo-method-bars", exoplanetMethods.slice(0, 6), "discovery_method", "planet_count");
      renderTable(
        "exo-table",
        [
          {
            key: "pl_name",
            label: "Planet",
            render: (row) =>
              `<button class="button" type="button" data-exoplanet-planet="${escapeHtml(row.pl_name)}">${escapeHtml(row.pl_name)}</button>`,
          },
          { key: "discovery_method", label: "Method" },
          { key: "disc_year", label: "Year" },
          { key: "sy_dist", label: "Distance (pc)", render: (row) => formatNumber(row.sy_dist, 2) },
        ],
        exoplanetCatalog.items
      );
      renderTable(
        "exoplanet-explorer",
        [
          {
            key: "pl_name",
            label: "Planet",
            render: (row) =>
              `<button class="button" type="button" data-exoplanet-planet="${escapeHtml(row.pl_name)}">${escapeHtml(row.pl_name)}</button>`,
          },
          { key: "discovery_method", label: "Method" },
          { key: "disc_year", label: "Year" },
        ],
        exoplanetCatalog.items
      );
      document.querySelectorAll("[data-exoplanet-planet]").forEach((button) => {
        button.addEventListener("click", () => loadExoplanetDetail(button.dataset.exoplanetPlanet));
      });
      state.explorers.exoplanet.offset = 0;
      state.explorers.exoplanet.limit = 8;
      renderExplorerMeta("exoplanet", exoplanetCatalog);
      setSectionStatus("exoplanet", "ok", `${formatNumber(exoplanetYears.length)} years`);
      await loadExoplanetPlanetFinder();
      if (exoplanetCatalog.items[0]?.pl_name) {
        document.querySelector("#exoplanet-planet-name").value = exoplanetCatalog.items[0].pl_name;
        await loadExoplanetDetail(exoplanetCatalog.items[0].pl_name);
      }
    }),
    loadSection(["osdr-summary", "osdr-explorer"], async () => {
      const [osdrSummary, osdrAssays, osdrDatasets] = await Promise.all([
        fetchJson("/analytics/osdr/dataset-summary"),
        fetchJson("/analytics/osdr/assay-type-summary"),
        fetchJson("/analytics/osdr/datasets?limit=8&offset=0"),
      ]);
      populateOsdrSourceOptions(osdrSummary);
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
      state.explorers.osdr.offset = 0;
      state.explorers.osdr.limit = 8;
      renderExplorerMeta("osdr", osdrDatasets);
      setSectionStatus("osdr", "ok", `${formatNumber(osdrSummary.length)} datasets`);
    }),
  ]);

  [
    ["overview", sectionResults[0]],
    ["ingestion", sectionResults[0]],
    ["neows", sectionResults[1]],
    ["eonet", sectionResults[2]],
    ["exoplanet", sectionResults[3]],
    ["osdr", sectionResults[4]],
  ].forEach(([section, ok]) => {
    if (!ok) {
      setSectionStatus(section, "warn", "Error");
    }
  });

  lastRefresh.textContent = sectionResults.every(Boolean)
    ? `Last refreshed ${new Date().toLocaleString()}`
    : `Partially refreshed ${new Date().toLocaleString()}`;
}

async function loadNeowsObjectFinder() {
  const query = document.querySelector("#neows-object-search").value.trim();
  const metaId = "neows-object-meta";
  document.querySelector(`#${metaId}`).textContent = query
    ? `Searching NeoWs objects for "${query}"...`
    : "Loading a few NeoWs object suggestions...";
  try {
    const params = new URLSearchParams({ limit: "12" });
    if (query) {
      params.set("query", query);
    }
    const items = await fetchJson(`/analytics/neows/objects?${params.toString()}`);
    renderNeowsObjectOptions(items);
    if (items.length === 0) {
      document.querySelector(`#${metaId}`).textContent = "No matching NeoWs objects found.";
      document.querySelector("#neows-object-summary").textContent =
        "No matching NeoWs objects were found for the current search.";
      return;
    }
    document.querySelector(`#${metaId}`).textContent = query
      ? `${formatNumber(items.length)} matching NeoWs objects found. Choose one to load details.`
      : `Showing ${formatNumber(items.length)} NeoWs suggestions. Choose one to load details.`;
  } catch (error) {
    document.querySelector(`#${metaId}`).textContent = "NeoWs object search unavailable";
    renderNeowsObjectOptions([]);
    document.querySelector("#neows-object-summary").textContent =
      "NeoWs search is unavailable right now, so the object summary could not be prepared.";
  }
}

async function loadNeowsObjectDetail(neoReferenceId) {
  const targetId = "neows-object-detail";
  const metaId = "neows-object-meta";
  if (!neoReferenceId) {
    document.querySelector(`#${metaId}`).textContent =
      "Enter a NeoWs object ID or click one of the KPI cards.";
    document.querySelector("#neows-object-summary").textContent =
      "Choose a NeoWs object to see a short generated summary.";
    document.querySelector("#neows-live-enrichment").textContent =
      "Live NASA enrichment has not been loaded yet.";
    document.querySelector("#neows-copilot").textContent =
      "Choose a NeoWs object to activate the first contextual copilot actions.";
    document.querySelector("#neows-approach-meta").textContent =
      "Choose a NeoWs object to view its recorded close approaches.";
    document.querySelector("#neows-approach-table").innerHTML = "";
    document.querySelector(`#${targetId}`).innerHTML = "";
    return;
  }

  setLoading(targetId);
  document.querySelector(`#${metaId}`).textContent = `Loading ${neoReferenceId}...`;
  document.querySelector("#neows-object-summary").textContent =
    `Preparing a NASAHub summary for ${neoReferenceId}...`;
  document.querySelector("#neows-live-enrichment").textContent =
    "Use 'Enrich from live NASA' to fetch a live summary from the NeoWs API.";
  document.querySelector("#neows-copilot").textContent =
    "Use the copilot actions to generate grounded NeoWs insights.";
  try {
    const payload = await fetchJson(`/analytics/neows/object/${encodeURIComponent(neoReferenceId)}`);
    state.neowsApproaches.currentObjectId = neoReferenceId;
    state.neowsApproaches.offset = 0;
    askModeSelect.value = "entity";
    askSourceSelect.value = "neows";
    askEntityInput.value = payload.neo_reference_id;
    updateAskModeState();
    document.querySelector(`#${metaId}`).textContent =
      `${payload.name} | ${payload.approach_count} recorded approaches | latest ${payload.most_recent_close_approach_date ?? "n/a"}`;
    document.querySelector("#neows-object-summary").textContent = buildNeowsObjectSummary(payload);
    renderDetailGrid(targetId, [
      { label: "Reference ID", value: escapeHtml(payload.neo_reference_id) },
      { label: "Hazardous", value: escapeHtml(payload.is_potentially_hazardous_asteroid ? "yes" : "no") },
      { label: "Sentry object", value: escapeHtml(payload.is_sentry_object ? "yes" : "no") },
      { label: "Absolute magnitude", value: escapeHtml(formatNumber(payload.absolute_magnitude_h, 2)) },
      { label: "Diameter min (km)", value: escapeHtml(formatNumber(payload.estimated_diameter_min_km, 3)) },
      { label: "Diameter max (km)", value: escapeHtml(formatNumber(payload.estimated_diameter_max_km, 3)) },
      { label: "First approach", value: escapeHtml(payload.first_close_approach_date ?? "n/a") },
      { label: "Recent approach", value: escapeHtml(payload.most_recent_close_approach_date ?? "n/a") },
      { label: "Closest miss (km)", value: escapeHtml(formatNumber(payload.min_miss_distance_km, 0)) },
      { label: "Max velocity (kph)", value: escapeHtml(formatNumber(payload.max_velocity_kph, 0)) },
      { label: "Latest orbiting body", value: escapeHtml(payload.latest_orbiting_body ?? "n/a") },
      {
        label: "JPL link",
        value: payload.nasa_jpl_url
          ? `<a href="${escapeHtml(payload.nasa_jpl_url)}" target="_blank" rel="noreferrer">Open source page</a>`
          : "n/a",
      },
    ]);
    await loadNeowsApproaches();
    await loadNeowsInsight(neoReferenceId, "overview");
  } catch (error) {
    document.querySelector(`#${metaId}`).textContent = "NeoWs object detail unavailable";
    document.querySelector("#neows-object-summary").textContent =
      "NASAHub could not generate an object summary because the object detail request failed.";
    document.querySelector("#neows-copilot").textContent =
      "NeoWs copilot is unavailable because the object detail request failed.";
    renderError(targetId, error.message);
  }
}

async function loadNeowsLiveEnrichment(neoReferenceId) {
  const target = document.querySelector("#neows-live-enrichment");
  if (!neoReferenceId) {
    target.textContent = "Choose a NeoWs object first, then request live NASA enrichment.";
    return;
  }
  target.textContent = `Fetching live NASA enrichment for ${neoReferenceId}...`;
  try {
    const payload = await fetchJson(
      `/analytics/neows/object/${encodeURIComponent(neoReferenceId)}/live-enrichment`
    );
    target.innerHTML = `
      <strong>Live NASA enrichment</strong><br />
      ${escapeHtml(payload.generated_summary)}<br /><br />
      <span class="muted">Source:</span>
      <a href="${escapeHtml(payload.source_url)}" target="_blank" rel="noreferrer">NeoWs live lookup</a>
    `;
  } catch (error) {
    target.textContent = `Live NASA enrichment failed: ${error.message}`;
  }
}

async function loadNeowsApproaches() {
  const targetId = "neows-approach-table";
  const neoReferenceId = state.neowsApproaches.currentObjectId;
  if (!neoReferenceId) {
    document.querySelector("#neows-approach-meta").textContent =
      "Choose a NeoWs object to view its recorded close approaches.";
    document.querySelector(`#${targetId}`).innerHTML = "";
    return;
  }

  setLoading(targetId);
  const { limit, offset } = state.neowsApproaches;
  try {
    const payload = await fetchJson(
      `/analytics/neows/object/${encodeURIComponent(neoReferenceId)}/approaches?limit=${limit}&offset=${offset}`
    );
    renderTable(
      targetId,
      [
        { key: "close_approach_date", label: "Date" },
        { key: "orbiting_body", label: "Body" },
        {
          key: "relative_velocity_km_per_hour",
          label: "Velocity (kph)",
          render: (row) => formatNumber(row.relative_velocity_km_per_hour, 0),
        },
        {
          key: "miss_distance_kilometers",
          label: "Miss distance (km)",
          render: (row) => formatNumber(row.miss_distance_kilometers, 0),
        },
        {
          key: "is_potentially_hazardous_asteroid",
          label: "Hazardous",
          render: (row) => escapeHtml(row.is_potentially_hazardous_asteroid ? "yes" : "no"),
        },
      ],
      payload.items
    );
    renderNeowsApproachMeta(payload);
  } catch (error) {
    document.querySelector("#neows-approach-meta").textContent =
      "Close approach history could not be loaded.";
    renderError(targetId, error.message);
  }
}

function changeNeowsApproachPage(direction) {
  const nextOffset = Math.max(0, state.neowsApproaches.offset + direction * state.neowsApproaches.limit);
  if (direction > 0 && nextOffset >= state.neowsApproaches.total) {
    return;
  }
  state.neowsApproaches.offset = nextOffset;
  loadNeowsApproaches();
}

async function loadNeowsInsight(neoReferenceId, mode) {
  const target = document.querySelector("#neows-copilot");
  if (!neoReferenceId) {
    target.textContent = "Choose a NeoWs object first to use the copilot.";
    return;
  }
  target.textContent = `Generating ${mode} insight for ${neoReferenceId}...`;
  try {
    const payload = await fetchJson(
      `/analytics/neows/object/${encodeURIComponent(neoReferenceId)}/insight?mode=${encodeURIComponent(mode)}`
    );
    target.innerHTML = `
      <strong>${escapeHtml(payload.title)}</strong><br />
      ${escapeHtml(payload.summary)}<br /><br />
      <span class="muted">Sources:</span> ${escapeHtml(payload.sources.join(", "))}
    `;
  } catch (error) {
    target.textContent = `NeoWs copilot failed: ${error.message}`;
  }
}

async function loadEonetDetail(eventId) {
  const targetId = "eonet-detail";
  const metaId = "eonet-detail-meta";
  if (!eventId) {
    document.querySelector(`#${metaId}`).textContent = "Choose an EONET event to view detail.";
    document.querySelector("#eonet-insight").textContent =
      "Choose an EONET event to activate contextual guidance.";
    document.querySelector(`#${targetId}`).innerHTML = "";
    return;
  }

  setLoading(targetId);
  document.querySelector(`#${metaId}`).textContent = `Loading ${eventId}...`;
  try {
    const payload = await fetchJson(`/analytics/eonet/event/${encodeURIComponent(eventId)}`);
    document.querySelector("#eonet-event-id").value = payload.event_id;
    askModeSelect.value = "entity";
    askSourceSelect.value = "eonet";
    askEntityInput.value = payload.event_id;
    updateAskModeState();
    document.querySelector(`#${metaId}`).textContent =
      `${payload.title} | ${payload.event_status} | ${payload.geometry_count} geometry update(s)`;
    renderDetailGrid(targetId, [
      { label: "Event ID", value: escapeHtml(payload.event_id) },
      { label: "Status", value: escapeHtml(payload.event_status) },
      { label: "Categories", value: escapeHtml(payload.category_titles ?? "n/a") },
      { label: "Sources", value: escapeHtml(payload.source_titles ?? "n/a") },
      { label: "Geometry count", value: escapeHtml(formatNumber(payload.geometry_count)) },
      { label: "Latest activity", value: escapeHtml(formatDate(payload.latest_geometry_at)) },
      { label: "Closed at", value: escapeHtml(formatDate(payload.closed_at)) },
      {
        label: "Reference link",
        value: payload.link
          ? `<a href="${escapeHtml(payload.link)}" target="_blank" rel="noreferrer">Open event page</a>`
          : "n/a",
      },
    ]);
    await loadEonetInsight(payload.event_id, "overview");
  } catch (error) {
    document.querySelector(`#${metaId}`).textContent = "EONET event detail unavailable";
    document.querySelector("#eonet-insight").textContent =
      "EONET contextual guidance is unavailable because the detail request failed.";
    renderError(targetId, error.message);
  }
}

async function loadEonetInsight(eventId, mode) {
  const target = document.querySelector("#eonet-insight");
  if (!eventId) {
    target.textContent = "Choose an EONET event first.";
    return;
  }
  target.textContent = `Generating ${mode} guidance for ${eventId}...`;
  try {
    const payload = await fetchJson(
      `/analytics/eonet/event/${encodeURIComponent(eventId)}/insight?mode=${encodeURIComponent(mode)}`
    );
    target.innerHTML = `
      <strong>${escapeHtml(payload.title)}</strong><br />
      ${escapeHtml(payload.summary)}<br /><br />
      <span class="muted">Sources:</span> ${escapeHtml(payload.sources.join(", "))}
    `;
  } catch (error) {
    target.textContent = `EONET guidance failed: ${error.message}`;
  }
}

async function loadExoplanetPlanetFinder() {
  const query = document.querySelector("#exoplanet-planet-name").value.trim();
  const metaId = "exoplanet-detail-meta";
  document.querySelector(`#${metaId}`).textContent = query
    ? `Searching exoplanets for "${query}"...`
    : "Loading exoplanet suggestions...";
  try {
    const params = new URLSearchParams({ limit: "12" });
    if (query) {
      params.set("query", query);
    }
    const items = await fetchJson(`/analytics/exoplanet/planets?${params.toString()}`);
    renderExoplanetPlanetOptions(items);
    document.querySelector(`#${metaId}`).textContent = items.length
      ? `Found ${formatNumber(items.length)} matching planets.`
      : "No matching exoplanets found.";
  } catch (error) {
    document.querySelector(`#${metaId}`).textContent = "Exoplanet search unavailable";
    renderExoplanetPlanetOptions([]);
  }
}

async function loadExoplanetDetail(plName) {
  const targetId = "exoplanet-detail";
  const metaId = "exoplanet-detail-meta";
  if (!plName) {
    document.querySelector(`#${metaId}`).textContent = "Choose an exoplanet to view detail.";
    document.querySelector("#exoplanet-insight").textContent =
      "Choose an exoplanet to activate contextual guidance.";
    document.querySelector(`#${targetId}`).innerHTML = "";
    return;
  }

  setLoading(targetId);
  document.querySelector(`#${metaId}`).textContent = `Loading ${plName}...`;
  try {
    const payload = await fetchJson(`/analytics/exoplanet/planet/${encodeURIComponent(plName)}`);
    document.querySelector("#exoplanet-planet-name").value = payload.pl_name;
    askModeSelect.value = "entity";
    askSourceSelect.value = "exoplanet";
    askEntityInput.value = payload.pl_name;
    updateAskModeState();
    document.querySelector(`#${metaId}`).textContent =
      `${payload.pl_name} | ${payload.discovery_method} | ${payload.hostname ?? "host unknown"}`;
    renderDetailGrid(targetId, [
      { label: "Planet", value: escapeHtml(payload.pl_name) },
      { label: "Host star", value: escapeHtml(payload.hostname ?? "n/a") },
      { label: "Discovery method", value: escapeHtml(payload.discovery_method) },
      { label: "Discovery year", value: escapeHtml(payload.disc_year ?? "n/a") },
      { label: "Distance (pc)", value: escapeHtml(formatNumber(payload.sy_dist, 2)) },
      { label: "Orbital period (days)", value: escapeHtml(formatNumber(payload.pl_orbper, 2)) },
      { label: "Radius", value: escapeHtml(formatNumber(payload.pl_rade, 2)) },
      { label: "Mass", value: escapeHtml(formatNumber(payload.pl_bmasse, 2)) },
      { label: "Host temp", value: escapeHtml(formatNumber(payload.st_teff, 0)) },
      { label: "Last ingested", value: escapeHtml(formatDate(payload.last_ingested_at)) },
    ]);
    await loadExoplanetInsight(payload.pl_name, "overview");
  } catch (error) {
    document.querySelector(`#${metaId}`).textContent = "Exoplanet detail unavailable";
    document.querySelector("#exoplanet-insight").textContent =
      "Exoplanet contextual guidance is unavailable because the detail request failed.";
    renderError(targetId, error.message);
  }
}

async function loadExoplanetInsight(plName, mode) {
  const target = document.querySelector("#exoplanet-insight");
  if (!plName) {
    target.textContent = "Choose an exoplanet first.";
    return;
  }
  target.textContent = `Generating ${mode} guidance for ${plName}...`;
  try {
    const payload = await fetchJson(
      `/analytics/exoplanet/planet/${encodeURIComponent(plName)}/insight?mode=${encodeURIComponent(mode)}`
    );
    target.innerHTML = `
      <strong>${escapeHtml(payload.title)}</strong><br />
      ${escapeHtml(payload.summary)}<br /><br />
      <span class="muted">Sources:</span> ${escapeHtml(payload.sources.join(", "))}
    `;
  } catch (error) {
    target.textContent = `Exoplanet guidance failed: ${error.message}`;
  }
}

async function loadAskNasaHub() {
  const mode = askModeSelect.value;
  const source = askSourceSelect.value;
  const entityId = askEntityInput.value.trim();
  const question = document.querySelector("#ask-question").value.trim();
  const includeLive = document.querySelector("#ask-include-live").checked;
  const target = document.querySelector("#ask-nasahub-response");

  if (!question) {
    target.textContent = "Provide a question first.";
    return;
  }

  if (mode === "entity" && !entityId) {
    target.textContent = "Entity mode needs a selected object, event, or planet.";
    return;
  }

  target.textContent = `Asking NASAHub about ${mode === "general" ? "your general question" : entityId}...`;
  try {
    const history = state.askHistory.slice(-6);
    const response = await fetch("/analytics/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...requestHeaders(),
      },
      body: JSON.stringify({
        mode,
        source,
        entity_id: mode === "entity" ? entityId : null,
        question,
        include_live_enrichment: includeLive,
        history,
      }),
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${body}`);
    }
    const payload = await response.json();
    state.askHistory = payload.conversation ?? [
      ...history,
      { role: "user", content: question },
      { role: "assistant", content: payload.answer },
    ];
    persistAskHistory();
    renderAskHistory();
    target.innerHTML = `
      <strong>Ask NASAHub</strong><br />
      <span class="muted">Mode:</span> ${escapeHtml(payload.mode)}<br />
      <span class="muted">Resolved source:</span> ${escapeHtml(payload.source)}<br />
      <span class="muted">Entity:</span> ${escapeHtml(payload.entity_id ?? "not required")}<br /><br />
      ${escapeHtml(payload.answer)}<br /><br />
      <span class="muted">Model:</span> ${escapeHtml(payload.model)}<br />
      <span class="muted">Grounded sources:</span> ${escapeHtml(payload.grounded_sources.join(", "))}<br /><br />
      <strong>Matched entities</strong><br />
      ${renderMatchedEntities(payload.matched_entities)}<br /><br />
      <strong>Citations</strong>
      ${renderCitations(payload.citations)}
    `;
  } catch (error) {
    target.textContent = `Ask NASAHub failed: ${error.message}`;
  }
}

async function loadEonetExplorer(reset = true) {
  setLoading("eonet-explorer");
  try {
    if (reset) {
      state.explorers.eonet.offset = 0;
    }
    const category = document.querySelector("#eonet-category").value.trim();
    const status = document.querySelector("#eonet-status").value;
    const { limit, offset } = state.explorers.eonet;
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (category) params.set("category_id", category);
    if (status) params.set("event_status", status);
    const payload = await fetchJson(`/analytics/eonet/event-overview?${params.toString()}`);
    renderTable(
      "eonet-explorer",
      [
        {
          key: "event_id",
          label: "Event",
          render: (row) =>
            `<button class="button" type="button" data-eonet-event="${escapeHtml(row.event_id)}">${escapeHtml(row.event_id)}</button>`,
        },
        { key: "category_titles", label: "Categories" },
        { key: "event_status", label: "Status" },
        { key: "latest_geometry_at", label: "Latest activity", render: (row) => escapeHtml(formatDate(row.latest_geometry_at)) },
        ],
      payload.items
    );
    document.querySelectorAll("[data-eonet-event]").forEach((button) => {
      button.addEventListener("click", () => loadEonetDetail(button.dataset.eonetEvent));
    });
    renderExplorerMeta("eonet", payload, [
      category ? `category=${category}` : "",
      status ? `status=${status}` : "",
    ]);
  } catch (error) {
    renderError("eonet-explorer", error.message);
  }
}

async function loadExoplanetExplorer(reset = true) {
  setLoading("exoplanet-explorer");
  try {
    if (reset) {
      state.explorers.exoplanet.offset = 0;
    }
    const method = document.querySelector("#exoplanet-method").value.trim();
    const year = document.querySelector("#exoplanet-year").value.trim();
    const { limit, offset } = state.explorers.exoplanet;
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (method) params.set("discovery_method", method);
    if (year) params.set("disc_year", year);
    const payload = await fetchJson(`/analytics/exoplanet/catalog?${params.toString()}`);
    renderTable(
      "exoplanet-explorer",
      [
        {
          key: "pl_name",
          label: "Planet",
          render: (row) =>
            `<button class="button" type="button" data-exoplanet-planet="${escapeHtml(row.pl_name)}">${escapeHtml(row.pl_name)}</button>`,
        },
        { key: "discovery_method", label: "Method" },
        { key: "disc_year", label: "Year" },
        { key: "sy_dist", label: "Distance (pc)", render: (row) => formatNumber(row.sy_dist, 2) },
        ],
      payload.items
    );
    document.querySelectorAll("[data-exoplanet-planet]").forEach((button) => {
      button.addEventListener("click", () => loadExoplanetDetail(button.dataset.exoplanetPlanet));
    });
    renderExplorerMeta("exoplanet", payload, [
      method ? `method=${method}` : "",
      year ? `year=${year}` : "",
    ]);
  } catch (error) {
    renderError("exoplanet-explorer", error.message);
  }
}

async function loadOsdrExplorer(reset = true) {
  setLoading("osdr-explorer");
  try {
    if (reset) {
      state.explorers.osdr.offset = 0;
    }
    const accession = document.querySelector("#osdr-accession").value.trim();
    const source = document.querySelector("#osdr-source").value.trim();
    const { limit, offset } = state.explorers.osdr;
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
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
    renderExplorerMeta("osdr", payload, [
      accession ? `accession=${accession}` : "",
      source ? `source=${source}` : "",
    ]);
  } catch (error) {
    renderError("osdr-explorer", error.message);
  }
}

function changeExplorerPage(explorerKey, direction) {
  const page = state.explorers[explorerKey];
  const nextOffset = Math.max(0, page.offset + direction * page.limit);
  if (direction > 0 && nextOffset >= page.total) {
    return;
  }
  page.offset = nextOffset;
  if (explorerKey === "eonet") {
    loadEonetExplorer(false);
  } else if (explorerKey === "exoplanet") {
    loadExoplanetExplorer(false);
  } else if (explorerKey === "osdr") {
    loadOsdrExplorer(false);
  }
}

setDashboardView(state.view);
loadDashboard();
