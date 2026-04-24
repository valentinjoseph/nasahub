const tokenInput = document.querySelector("#api-token");
const loginForm = document.querySelector("#login-form");
const loginUsername = document.querySelector("#login-username");
const loginPassword = document.querySelector("#login-password");
const loginStatus = document.querySelector("#login-status");
const logoutButton = document.querySelector("#logout-button");
const refreshButton = document.querySelector("#refresh-all");
const lastRefresh = document.querySelector("#last-refresh");
const apiModeIndicator = document.querySelector("#api-mode-indicator");
const askModeSelect = document.querySelector("#ask-mode");
const askSourceSelect = document.querySelector("#ask-source");
const askEntityInput = document.querySelector("#ask-entity-id");
const askComparisonEntityInput = document.querySelector("#ask-comparison-entity-id");

function getStoredJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (error) {
    return fallback;
  }
}

function hasCookie(name) {
  return document.cookie
    .split(";")
    .map((item) => item.trim())
    .some((item) => item === `${name}=1`);
}

function getCookieValue(name) {
  const prefix = `${name}=`;
  const match = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix));
  return match ? decodeURIComponent(match.slice(prefix.length)) : "";
}

const initialViewerMode = hasCookie("nasahub_viewer_mode");
const initialLoginRole = getCookieValue("nasahub_login_role");

function storageKey(name, viewerMode = initialViewerMode, loginRole = initialLoginRole) {
  if (viewerMode) {
    return `nasahub_viewer_${name}`;
  }
  if (["guest", "user"].includes(loginRole)) {
    return `nasahub_${loginRole}_${name}`;
  }
  return `nasahub_${name}`;
}

const state = {
  token: sessionStorage.getItem("nasahub_api_token") || "",
  viewerMode: initialViewerMode,
  loginRole: ["admin", "user", "guest"].includes(initialLoginRole) ? initialLoginRole : "",
  askHistory: getStoredJson(storageKey("ask_history"), []),
  pins: getStoredJson(storageKey("pins"), []),
  recentComparisons: getStoredJson(storageKey("recent_comparisons"), []),
  savedContexts: getStoredJson(storageKey("saved_contexts"), []),
  view: "overview",
  workspaceView: "ask",
  currentEntities: {
    neows: "",
    eonet: "",
    exoplanet: "",
    osdr: "",
  },
  lastAskResponse: null,
  explorerRows: {
    neows: [],
    eonet: [],
    exoplanet: [],
    osdr: [],
  },
  ingestionStatus: [],
  loadedViews: {
    overview: false,
    neows: false,
    eonet: false,
    exoplanet: false,
    osdr: false,
    workspace: false,
  },
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

if (tokenInput) {
  tokenInput.value = state.token;
}
updateApiModeIndicator();

if (tokenInput) {
  tokenInput.addEventListener("change", () => {
    state.token = tokenInput.value.trim();
    if (state.token) {
      sessionStorage.setItem("nasahub_api_token", state.token);
    } else {
      sessionStorage.removeItem("nasahub_api_token");
    }
    updateApiModeIndicator();
  });
}

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await loginWithAccount();
  });
}

if (logoutButton) {
  logoutButton.addEventListener("click", () => {
    window.location.href = "/logout";
  });
}

if (refreshButton) {
  refreshButton.addEventListener("click", () => {
    refreshCurrentView();
  });
}

document.querySelector('[data-action="load-eonet"]').addEventListener("click", loadEonetExplorer);
document.querySelector('[data-action="load-exoplanet"]').addEventListener("click", loadExoplanetExplorer);
document.querySelector('[data-action="load-osdr"]').addEventListener("click", loadOsdrExplorer);
document.querySelector("#load-eonet-detail").addEventListener("click", () => {
  loadEonetDetail(document.querySelector("#eonet-event-id").value.trim());
});
document.querySelector("#eonet-use-in-ask").addEventListener("click", () => {
  useCurrentEntityInAsk("eonet", document.querySelector("#eonet-event-id").value.trim(), false);
});
document.querySelector("#eonet-use-as-comparison").addEventListener("click", () => {
  useCurrentEntityInAsk("eonet", document.querySelector("#eonet-event-id").value.trim(), true);
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
document.querySelector("#exoplanet-use-in-ask").addEventListener("click", () => {
  useCurrentEntityInAsk("exoplanet", document.querySelector("#exoplanet-planet-name").value.trim(), false);
});
document.querySelector("#exoplanet-use-as-comparison").addEventListener("click", () => {
  useCurrentEntityInAsk("exoplanet", document.querySelector("#exoplanet-planet-name").value.trim(), true);
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
document.querySelector("#neows-use-in-ask").addEventListener("click", () => {
  useCurrentEntityInAsk("neows", document.querySelector("#neows-object-id").value.trim(), false);
});
document.querySelector("#neows-use-as-comparison").addEventListener("click", () => {
  useCurrentEntityInAsk("neows", document.querySelector("#neows-object-id").value.trim(), true);
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
document.querySelector("#workspace-neows-search").addEventListener("click", loadWorkspaceNeowsExplorer);
document.querySelector("#workspace-neows-results").addEventListener("change", (event) => {
  if (event.target.value) {
    renderWorkspaceNeowsSelection(event.target.value);
  }
});
document.querySelector("#workspace-neows-load").addEventListener("click", async () => {
  const neoReferenceId = document.querySelector("#workspace-neows-results").value.trim();
  if (!neoReferenceId) {
    return;
  }
  document.querySelector("#neows-object-id").value = neoReferenceId;
  await setDashboardView("neows");
  loadNeowsObjectDetail(neoReferenceId);
});
document.querySelector("#workspace-neows-use").addEventListener("click", () => {
  useCurrentEntityInAsk("neows", document.querySelector("#workspace-neows-results").value.trim(), false);
});
document.querySelector("#workspace-neows-compare").addEventListener("click", () => {
  useCurrentEntityInAsk("neows", document.querySelector("#workspace-neows-results").value.trim(), true);
});
document.querySelector("#neows-approach-prev").addEventListener("click", () => changeNeowsApproachPage(-1));
document.querySelector("#neows-approach-next").addEventListener("click", () => changeNeowsApproachPage(1));
document.querySelector("#eonet-prev").addEventListener("click", () => changeExplorerPage("eonet", -1));
document.querySelector("#eonet-next").addEventListener("click", () => changeExplorerPage("eonet", 1));
document.querySelector("#exoplanet-prev").addEventListener("click", () => changeExplorerPage("exoplanet", -1));
document.querySelector("#exoplanet-next").addEventListener("click", () => changeExplorerPage("exoplanet", 1));
document.querySelector("#osdr-prev").addEventListener("click", () => changeExplorerPage("osdr", -1));
document.querySelector("#osdr-next").addEventListener("click", () => changeExplorerPage("osdr", 1));
document.querySelector("#eonet-reset").addEventListener("click", resetEonetExplorerFilters);
document.querySelector("#exoplanet-reset").addEventListener("click", resetExoplanetExplorerFilters);
document.querySelector("#osdr-reset").addEventListener("click", resetOsdrExplorerFilters);
document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", async () => {
    await setDashboardView(button.dataset.view);
  });
});
document.querySelectorAll("[data-workspace-view]").forEach((button) => {
  button.addEventListener("click", () => {
    setWorkspaceView(button.dataset.workspaceView);
  });
});
document.querySelectorAll("[data-collapsible-target]").forEach((button) => {
  button.addEventListener("click", () => {
    toggleCollapsible(button.dataset.collapsibleTarget, button);
  });
});
document.querySelector("#ask-nasahub").addEventListener("click", loadAskNasaHub);
document.querySelector("#clear-ask-history").addEventListener("click", clearAskHistory);
document.querySelector("#save-ask-context").addEventListener("click", saveCurrentAskContext);
document.querySelector("#share-ask-context").addEventListener("click", copyAskShareLink);
document.querySelector("#export-ask-response").addEventListener("click", exportAskResponse);
askModeSelect.addEventListener("change", updateAskModeState);
askSourceSelect.addEventListener("change", () => {
  renderAskSuggestions();
  renderAskContextBanner();
});
askEntityInput.addEventListener("input", () => {
  renderAskSuggestions();
  renderAskContextBanner();
});
askComparisonEntityInput.addEventListener("input", () => {
  renderAskSuggestions();
  renderAskContextBanner();
});
document.querySelector("#neows-pin-current").addEventListener("click", () => {
  pinEntity("neows", document.querySelector("#neows-object-id").value.trim(), state.currentEntities.neows);
});
document.querySelector("#eonet-pin-current").addEventListener("click", () => {
  pinEntity("eonet", document.querySelector("#eonet-event-id").value.trim(), state.currentEntities.eonet);
});
document.querySelector("#exoplanet-pin-current").addEventListener("click", () => {
  pinEntity("exoplanet", document.querySelector("#exoplanet-planet-name").value.trim(), state.currentEntities.exoplanet);
});
document.querySelector("#workspace-neows-share").addEventListener("click", () => copyExplorerShareLink("neows"));
document.querySelector("#workspace-neows-export").addEventListener("click", () => exportRows("neows", "json"));
document.querySelector("#eonet-share").addEventListener("click", () => copyExplorerShareLink("eonet"));
document.querySelector("#eonet-export").addEventListener("click", () => exportRows("eonet", "csv"));
document.querySelector("#exoplanet-share").addEventListener("click", () => copyExplorerShareLink("exoplanet"));
document.querySelector("#exoplanet-export").addEventListener("click", () => exportRows("exoplanet", "csv"));
document.querySelector("#osdr-share").addEventListener("click", () => copyExplorerShareLink("osdr"));
document.querySelector("#osdr-export").addEventListener("click", () => exportRows("osdr", "csv"));

renderAskHistory();
updateAskModeState();
renderAskSuggestions();
applySharedStateFromUrl();
updateAskModeState();
renderSessionShelf();

function requestHeaders() {
  if (state.token) {
    return {
      "X-API-Key": state.token,
    };
  }
  return {};
}

function isViewerMode() {
  return Boolean(state.viewerMode && !state.token);
}

function isGuestLogin() {
  return Boolean(state.loginRole === "guest" && !state.token);
}

function usesLocalShelf() {
  return isViewerMode() || isGuestLogin();
}

async function fetchJson(path) {
  const response = await fetch(path, {
    headers: requestHeaders(),
    credentials: "same-origin",
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
  const normalized = String(message || "");
  const isUnauthorized = normalized.includes("401 Unauthorized");
  const isForbidden = normalized.includes("403 Forbidden");
  const title = isUnauthorized ? "Authentication needed" : "Something needs attention";
  const guidance = isUnauthorized
    ? isViewerMode()
      ? "Shared access is active, but this route still needs an account. Sign in from the NASAHub home page."
      : "Sign in with a guest, user, or admin account from the NASAHub home page."
    : isForbidden && isGuestLogin()
      ? "Guest login can explore analytics but cannot use protected admin actions or Ask NASAHub."
    : "NASAHub could not complete this request yet. Try refreshing this workspace or switching views and coming back.";
  document.querySelector(
    `#${targetId}`
  ).innerHTML = `
    <div class="error-box">
      <div class="error-box__title">${escapeHtml(title)}</div>
      <div>${escapeHtml(guidance)}</div>
      <div class="muted error-box__detail">${escapeHtml(normalized)}</div>
    </div>
  `;
}

function renderStatePanel(targetId, { eyebrow = "", title, body, items = [], tone = "calm" }) {
  document.querySelector(`#${targetId}`).innerHTML = `
    <div class="state-panel state-panel--${escapeHtml(tone)}">
      ${eyebrow ? `<div class="state-panel__eyebrow">${escapeHtml(eyebrow)}</div>` : ""}
      <div class="state-panel__title">${escapeHtml(title)}</div>
      <div class="state-panel__body">${escapeHtml(body)}</div>
      ${
        items.length
          ? `<div class="state-panel__list">${items
              .map((item) => `<span>${escapeHtml(item)}</span>`)
              .join("")}</div>`
          : ""
      }
    </div>
  `;
}

function updateApiModeIndicator() {
  const modeBanner = document.querySelector("#mode-banner");
  if (loginStatus) {
    loginStatus.textContent = state.loginRole
      ? `Signed in as ${state.loginRole}.`
      : "Sign in from the NASAHub home page.";
  }
  if (state.token) {
    apiModeIndicator.className = "section-badge section-badge--ok";
    apiModeIndicator.textContent = "Authenticated";
    updateModeBanner(modeBanner, "mode-banner mode-banner--admin", "Authenticated access: analytics, Ask NASAHub, saved contexts, and pins are available.");
    updateGuestChatAccess();
    return;
  }
  if (state.loginRole === "admin") {
    apiModeIndicator.className = "section-badge section-badge--ok";
    apiModeIndicator.textContent = "Admin account";
    updateModeBanner(modeBanner, "mode-banner mode-banner--admin", "Admin login: analytics, Ask NASAHub, saved contexts, and pinned items are available.");
    updateGuestChatAccess();
    return;
  }
  if (state.loginRole === "user") {
    apiModeIndicator.className = "section-badge section-badge--ok";
    apiModeIndicator.textContent = "User account";
    updateModeBanner(modeBanner, "mode-banner mode-banner--admin", "User login: analytics and Ask NASAHub are available.");
    updateGuestChatAccess();
    return;
  }
  if (state.loginRole === "guest") {
    apiModeIndicator.className = "section-badge section-badge--ok";
    apiModeIndicator.textContent = "Guest account";
    updateModeBanner(modeBanner, "mode-banner mode-banner--guest", "Guest account: analytics are available, while Ask NASAHub and shared workspace actions stay locked.");
    updateGuestChatAccess();
    return;
  }
  if (state.viewerMode) {
    apiModeIndicator.className = "section-badge section-badge--ok";
    apiModeIndicator.textContent = "Shared access";
    updateModeBanner(modeBanner, "mode-banner mode-banner--guest", "Shared access is active. For account permissions, sign in from the NASAHub home page.");
    updateGuestChatAccess();
    return;
  }
  apiModeIndicator.className = "section-badge section-badge--loading";
  apiModeIndicator.textContent = "Signed out";
  updateModeBanner(modeBanner, "mode-banner mode-banner--guest", "Sign in from the NASAHub home page with a guest, user, or admin account.");
  updateGuestChatAccess();
}

function updateModeBanner(target, className, text) {
  if (!target) {
    return;
  }
  target.className = className;
  target.textContent = text;
}

async function loginWithAccount() {
  loginStatus.textContent = "Signing in...";
  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "same-origin",
      body: JSON.stringify({
        username: loginUsername.value,
        password: loginPassword.value,
      }),
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${body}`);
    }
    const payload = await response.json();
    state.loginRole = payload.role;
    state.viewerMode = false;
    state.askHistory = getStoredJson(storageKey("ask_history", state.viewerMode, state.loginRole), []);
    state.pins = getStoredJson(storageKey("pins", state.viewerMode, state.loginRole), []);
    state.recentComparisons = getStoredJson(storageKey("recent_comparisons", state.viewerMode, state.loginRole), []);
    state.savedContexts = getStoredJson(storageKey("saved_contexts", state.viewerMode, state.loginRole), []);
    loginPassword.value = "";
    updateApiModeIndicator();
    renderAskHistory();
    renderSessionShelf();
    await refreshCurrentView();
  } catch (error) {
    loginStatus.textContent = `Login failed: ${error.message}`;
  }
}

function updateGuestChatAccess() {
  const guestBlocked = isGuestLogin();
  document.querySelector("#ask-nasahub").disabled = guestBlocked;
  document.querySelector("#save-ask-context").disabled = guestBlocked;
  document.querySelector("#share-ask-context").disabled = false;
  document.querySelector("#export-ask-response").disabled = false;
  applyGuestWorkspaceAccess(guestBlocked);
  if (guestBlocked) {
    renderStatePanel("ask-nasahub-response", {
      eyebrow: "Guest access",
      title: "Ask NASAHub is locked for guest",
      body: "Guest can browse analytics. Sign in with a user or admin account to use the chatbot.",
      tone: "warning",
    });
  }
}

function applyGuestWorkspaceAccess(guestBlocked) {
  const workspaceButton = document.querySelector('[data-view="workspace"]');
  const assistantButton = document.querySelector('[data-workspace-view="ask"]');
  const askPanel = document.querySelector('[data-workspace-panel="ask"]');
  const workspaceTitle = document.querySelector('[data-panel-group="workspace"] .panel__head h2');
  const workspaceCopy = document.querySelector('[data-panel-group="workspace"] .panel__head p');

  if (workspaceButton) {
    workspaceButton.textContent = guestBlocked ? "Explore" : "Ask & Explore";
  }
  if (assistantButton) {
    assistantButton.hidden = guestBlocked;
  }
  if (askPanel) {
    askPanel.hidden = guestBlocked || state.workspaceView !== "ask";
  }
  if (workspaceTitle) {
    workspaceTitle.textContent = guestBlocked ? "Explore NASAHub" : "Ask NASAHub";
  }
  if (workspaceCopy) {
    workspaceCopy.textContent = guestBlocked
      ? "Use the source explorers for read-only analysis across curated NASAHub data."
      : "Use the agent workspace for grounded questions, matched entities, comparisons, and guided follow-up prompts.";
  }
  if (guestBlocked && state.workspaceView === "ask") {
    setWorkspaceView("neows");
  }
}

function persistAskHistory() {
  localStorage.setItem(
    storageKey("ask_history", state.viewerMode, state.loginRole),
    JSON.stringify(state.askHistory.slice(-8))
  );
}

function persistPins() {
  localStorage.setItem(storageKey("pins", state.viewerMode, state.loginRole), JSON.stringify(state.pins.slice(0, 12)));
}

function persistRecentComparisons() {
  localStorage.setItem(
    storageKey("recent_comparisons", state.viewerMode, state.loginRole),
    JSON.stringify(state.recentComparisons.slice(-8))
  );
}

function persistSavedContexts() {
  localStorage.setItem(
    storageKey("saved_contexts", state.viewerMode, state.loginRole),
    JSON.stringify(state.savedContexts.slice(0, 8))
  );
}

function persistIngestionStatus(items) {
  state.ingestionStatus = items;
}

function sourceLabel(source) {
  const labels = {
    neows: "NeoWs",
    eonet: "EONET",
    exoplanet: "Exoplanet",
    osdr: "OSDR",
    general: "All sources",
  };
  return labels[source] ?? source;
}

function truncateText(value, maxLength = 110) {
  if (!value) {
    return "";
  }
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value;
}

function upsertFront(items, candidate, matcher, limit) {
  return [candidate, ...items.filter((item) => !matcher(item, candidate))].slice(0, limit);
}

function pinEntity(source, entityId, label, options = {}) {
  if (!entityId) {
    document.querySelector("#ask-nasahub-response").textContent =
      "Load a real record first, then pin it for later.";
    return;
  }
  const candidate = {
    source,
    entityId,
    label: label || entityId,
    watchlist: Boolean(options.watchlist),
    savedAt: new Date().toISOString(),
  };
  savePinToBackend(candidate);
}

function saveCurrentAskContext() {
  const mode = askModeSelect.value;
  const source = askSourceSelect.value;
  const entityId = askEntityInput.value.trim();
  const comparisonEntityId = askComparisonEntityInput.value.trim();
  const question = document.querySelector("#ask-question").value.trim();
  const includeLive = document.querySelector("#ask-include-live").checked;

  if (mode === "entity" && !entityId) {
    document.querySelector("#ask-nasahub-response").textContent =
      "Choose an entity before saving an entity-mode context.";
    return;
  }

  if (!question && mode === "general" && source === "general") {
    document.querySelector("#ask-nasahub-response").textContent =
      "Add at least a source, an entity, or a question before saving a context.";
    return;
  }

  const candidate = {
    label: buildSavedContextLabel(mode, source, entityId, comparisonEntityId, question),
    mode,
    source,
    entityId,
    comparisonEntityId,
    question,
    includeLive,
    savedAt: new Date().toISOString(),
  };
  saveContextToBackend(candidate);
}

function rememberRecentComparison(source, entityId, comparisonEntityId, question) {
  if (!source || !entityId || !comparisonEntityId) {
    return;
  }
  const candidate = {
    source,
    entityId,
    comparisonEntityId,
    question,
    savedAt: new Date().toISOString(),
  };
  state.recentComparisons = upsertFront(
    state.recentComparisons,
    candidate,
    (item, next) =>
      item.source === next.source &&
      item.entityId === next.entityId &&
      item.comparisonEntityId === next.comparisonEntityId,
    8
  );
  persistRecentComparisons();
  renderSessionShelf();
}

function buildSavedContextLabel(mode, source, entityId, comparisonEntityId, question) {
  if (question) {
    return truncateText(question, 58);
  }
  if (mode === "general") {
    return `${sourceLabel(source)} general analysis`;
  }
  if (comparisonEntityId) {
    return `${entityId} vs ${comparisonEntityId}`;
  }
  return `${sourceLabel(source)} context`;
}

async function saveContextToBackend(candidate) {
  const target = document.querySelector("#ask-nasahub-response");
  if (usesLocalShelf()) {
    state.savedContexts = upsertFront(
      state.savedContexts,
      candidate,
      (item, next) =>
        item.mode === next.mode &&
        item.source === next.source &&
        item.entityId === next.entityId &&
        item.comparisonEntityId === next.comparisonEntityId &&
        item.question === next.question,
      8
    );
    persistSavedContexts();
    renderSessionShelf();
    target.textContent = isGuestLogin()
      ? "Saved locally for this guest login. Ask contexts are not shared to the Lenovo from guest mode."
      : "Saved locally for this browser session.";
    return;
  }
  target.textContent = "Saving current context to NASAHub...";
  try {
    const response = await fetch("/analytics/saved-contexts", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...requestHeaders(),
      },
      body: JSON.stringify({
        label: candidate.label,
        mode: candidate.mode,
        source: candidate.source,
        entity_id: candidate.entityId || null,
        comparison_entity_id: candidate.comparisonEntityId || null,
        question: candidate.question || "",
        include_live_enrichment: candidate.includeLive,
      }),
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${body}`);
    }
    await loadSavedContextsFromBackend();
    target.textContent =
      "Current Ask NASAHub context saved on the Lenovo and mirrored into the session shelf.";
  } catch (error) {
    state.savedContexts = upsertFront(
      state.savedContexts,
      candidate,
      (item, next) =>
        item.mode === next.mode &&
        item.source === next.source &&
        item.entityId === next.entityId &&
        item.comparisonEntityId === next.comparisonEntityId &&
        item.question === next.question,
      8
    );
    persistSavedContexts();
    renderSessionShelf();
    target.textContent =
      `Saved locally because backend persistence was unavailable: ${error.message}`;
  }
}

async function loadSavedContextsFromBackend() {
  if (usesLocalShelf()) {
    state.savedContexts = getStoredJson(storageKey("saved_contexts", state.viewerMode, state.loginRole), []);
    renderSessionShelf();
    return;
  }
  try {
    const items = await fetchJson("/analytics/saved-contexts");
    state.savedContexts = items.map((item) => ({
      contextId: item.context_id,
      label: item.label,
      mode: item.mode,
      source: item.source,
      entityId: item.entity_id ?? "",
      comparisonEntityId: item.comparison_entity_id ?? "",
      question: item.question ?? "",
      includeLive: item.include_live_enrichment,
      savedAt: item.updated_at ?? item.created_at,
      backend: true,
    }));
    persistSavedContexts();
  } catch (error) {
    state.savedContexts = getStoredJson(storageKey("saved_contexts", state.viewerMode, state.loginRole), []);
  }
  renderSessionShelf();
}

async function savePinToBackend(candidate) {
  const target = document.querySelector("#ask-nasahub-response");
  if (usesLocalShelf()) {
    state.pins = upsertFront(
      state.pins,
      candidate,
      (item, next) => item.source === next.source && item.entityId === next.entityId,
      12
    );
    persistPins();
    renderSessionShelf();
    target.textContent =
      `${candidate.label} is now ${candidate.watchlist ? "in your local watchlist" : "pinned locally"} for this ${
        isGuestLogin() ? "guest account" : "browser session"
      }.`;
    return;
  }
  target.textContent = `Saving ${candidate.label} to NASAHub...`;
  try {
    const response = await fetch("/analytics/pins", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...requestHeaders(),
      },
      body: JSON.stringify({
        source: candidate.source,
        entity_id: candidate.entityId,
        label: candidate.label,
        watchlist: candidate.watchlist,
      }),
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${body}`);
    }
    await loadPinsFromBackend();
    target.textContent =
      `${candidate.label} is now ${candidate.watchlist ? "in your watchlist" : "pinned"} on the Lenovo.`;
  } catch (error) {
    state.pins = upsertFront(
      state.pins,
      candidate,
      (item, next) => item.source === next.source && item.entityId === next.entityId,
      12
    );
    persistPins();
    renderSessionShelf();
    target.textContent =
      `Pinned locally because backend persistence was unavailable: ${error.message}`;
  }
}

async function loadPinsFromBackend() {
  if (usesLocalShelf()) {
    state.pins = getStoredJson(storageKey("pins", state.viewerMode, state.loginRole), []);
    renderSessionShelf();
    return;
  }
  try {
    const items = await fetchJson("/analytics/pins");
    state.pins = items.map((item) => ({
      pinId: item.pin_id,
      source: item.source,
      entityId: item.entity_id,
      label: item.label,
      watchlist: item.watchlist,
      savedAt: item.updated_at ?? item.created_at,
      backend: true,
    }));
    persistPins();
  } catch (error) {
    state.pins = getStoredJson(storageKey("pins", state.viewerMode, state.loginRole), []);
  }
  renderSessionShelf();
}

async function deletePin(pinId) {
  if (usesLocalShelf()) {
    return;
  }
  const response = await fetch(`/analytics/pins/${encodeURIComponent(pinId)}`, {
    method: "DELETE",
    headers: requestHeaders(),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  await loadPinsFromBackend();
}

async function restoreAskContext(context) {
  askModeSelect.value = context.mode ?? "entity";
  askSourceSelect.value = context.source ?? "general";
  askEntityInput.value = context.entityId ?? "";
  askComparisonEntityInput.value = context.comparisonEntityId ?? "";
  document.querySelector("#ask-question").value = context.question ?? "";
  document.querySelector("#ask-include-live").checked = Boolean(context.includeLive);
  updateAskModeState();
  renderAskContextBanner();
  setWorkspaceView("ask");
  await setDashboardView("workspace");
}

async function openPinnedEntity(source, entityId) {
  if (!entityId || !["neows", "eonet", "exoplanet", "osdr"].includes(source)) {
    return;
  }
  if (source === "osdr") {
    document.querySelector("#osdr-accession").value = entityId;
    await setDashboardView("workspace");
    setWorkspaceView("osdr");
    await loadOsdrExplorer();
    return;
  }
  await setDashboardView(source);
  if (source === "neows") {
    document.querySelector("#neows-object-id").value = entityId;
    await loadNeowsObjectDetail(entityId);
    return;
  }
  if (source === "eonet") {
    document.querySelector("#eonet-event-id").value = entityId;
    await loadEonetDetail(entityId);
    return;
  }
  document.querySelector("#exoplanet-planet-name").value = entityId;
  await loadExoplanetDetail(entityId);
}

function renderSessionShelf() {
  const pinnedTarget = document.querySelector("#pinned-items");
  const comparisonsTarget = document.querySelector("#recent-comparisons");
  const contextsTarget = document.querySelector("#saved-contexts");

  pinnedTarget.innerHTML = state.pins.length
    ? state.pins
        .map(
          (item, index) => `
            <article class="session-item">
              <div class="session-item__title">${escapeHtml(item.label)}</div>
              <div class="session-item__meta">${escapeHtml(sourceLabel(item.source))} | ${escapeHtml(item.entityId)} | Pinned ${escapeHtml(formatDate(item.savedAt))}${item.watchlist ? " | Watchlist" : ""}</div>
              <div class="session-item__actions">
                <button class="button button--ghost" type="button" data-session-action="use-pin" data-session-index="${index}">Use</button>
                <button class="button button--ghost" type="button" data-session-action="open-pin" data-session-index="${index}">Open</button>
                <button class="button button--ghost" type="button" data-session-action="remove-pin" data-session-index="${index}">Remove</button>
              </div>
            </article>
          `
        )
        .join("")
    : `<div class="session-empty">No pinned items yet. Pin a NeoWs object, EONET event, or Exoplanet to keep it close.</div>`;

  comparisonsTarget.innerHTML = state.recentComparisons.length
    ? state.recentComparisons
        .map(
          (item, index) => `
            <article class="session-item">
              <div class="session-item__title">${escapeHtml(sourceLabel(item.source))} comparison</div>
              <div class="session-item__meta">${escapeHtml(item.entityId)} vs ${escapeHtml(item.comparisonEntityId)}<br />${escapeHtml(truncateText(item.question || "No prompt stored"))}</div>
              <div class="session-item__actions">
                <button class="button button--ghost" type="button" data-session-action="restore-comparison" data-session-index="${index}">Restore</button>
                <button class="button button--ghost" type="button" data-session-action="remove-comparison" data-session-index="${index}">Remove</button>
              </div>
            </article>
          `
        )
        .join("")
    : `<div class="session-empty">Recent comparisons will appear here after you compare two entities through Ask NASAHub.</div>`;

  contextsTarget.innerHTML = state.savedContexts.length
    ? state.savedContexts
        .map(
          (item, index) => `
            <article class="session-item">
              <div class="session-item__title">${escapeHtml(item.label || (item.mode === "general" ? "General analysis" : `${sourceLabel(item.source)} context`))}</div>
              <div class="session-item__meta">${escapeHtml(item.entityId || sourceLabel(item.source))}${item.comparisonEntityId ? ` vs ${escapeHtml(item.comparisonEntityId)}` : ""}<br />${escapeHtml(truncateText(item.question || "No question saved"))}</div>
              <div class="session-item__actions">
                <button class="button button--ghost" type="button" data-session-action="restore-context" data-session-index="${index}">Restore</button>
                <button class="button button--ghost" type="button" data-session-action="ask-context" data-session-index="${index}">Ask</button>
                <button class="button button--ghost" type="button" data-session-action="remove-context" data-session-index="${index}">Remove</button>
              </div>
            </article>
          `
        )
        .join("")
    : `<div class="session-empty">Saved Ask NASAHub contexts will appear here once you save one from the assistant.</div>`;

  bindSessionActions();
}

function bindSessionActions() {
  document.querySelectorAll("[data-session-clear]").forEach((button) => {
    button.onclick = () => {
      const key = button.dataset.sessionClear;
      state[key] = [];
      if (key === "pins") {
        persistPins();
      } else if (key === "recentComparisons") {
        persistRecentComparisons();
      } else if (key === "savedContexts") {
        persistSavedContexts();
      }
      renderSessionShelf();
    };
  });

  document.querySelectorAll("[data-session-action]").forEach((button) => {
    button.onclick = async () => {
      const action = button.dataset.sessionAction;
      const index = Number(button.dataset.sessionIndex);
      if (action === "use-pin") {
        const item = state.pins[index];
        await useCurrentEntityInAsk(item.source, item.entityId, false);
        return;
      }
      if (action === "open-pin") {
        const item = state.pins[index];
        await openPinnedEntity(item.source, item.entityId);
        return;
      }
      if (action === "remove-pin") {
        const item = state.pins[index];
        if (item?.pinId) {
          await deletePin(item.pinId);
        } else {
          state.pins.splice(index, 1);
          persistPins();
          renderSessionShelf();
        }
        return;
      }
      if (action === "restore-comparison") {
        const item = state.recentComparisons[index];
        await restoreAskContext({
          mode: "entity",
          source: item.source,
          entityId: item.entityId,
          comparisonEntityId: item.comparisonEntityId,
          question: item.question,
          includeLive: false,
        });
        return;
      }
      if (action === "remove-comparison") {
        state.recentComparisons.splice(index, 1);
        persistRecentComparisons();
        renderSessionShelf();
        return;
      }
      if (action === "restore-context") {
        await restoreAskContext(state.savedContexts[index]);
        return;
      }
      if (action === "ask-context") {
        await restoreAskContext(state.savedContexts[index]);
        if (document.querySelector("#ask-question").value.trim()) {
          await loadAskNasaHub();
        }
        return;
      }
      if (action === "remove-context") {
        const item = state.savedContexts[index];
        if (item?.contextId) {
          await deleteSavedContext(item.contextId);
        } else {
          state.savedContexts.splice(index, 1);
          persistSavedContexts();
          renderSessionShelf();
        }
      }
    };
  });
}

function bindOsdrPinButtons() {
  document.querySelectorAll("[data-pin-osdr]").forEach((button) => {
    button.onclick = () => {
      const accession = button.dataset.pinOsdr;
      pinEntity("osdr", accession, accession, { watchlist: true });
    };
  });
}

async function deleteSavedContext(contextId) {
  if (usesLocalShelf()) {
    return;
  }
  const response = await fetch(`/analytics/saved-contexts/${encodeURIComponent(contextId)}`, {
    method: "DELETE",
    headers: requestHeaders(),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  await loadSavedContextsFromBackend();
}

function buildFreshnessSummary(source, timestamps = []) {
  const statusRows = state.ingestionStatus.filter((row) => row.source_name === source);
  const latestRun = statusRows
    .map((row) => row.latest_run_finished_at || row.latest_run_started_at)
    .filter(Boolean)
    .sort()
    .reverse()[0];
  const latestIngested = timestamps.filter(Boolean).sort().reverse()[0];
  const latest = latestIngested || latestRun;
  if (!latest) {
    return `No freshness signal is available yet for ${sourceLabel(source)}.`;
  }
  const age = formatRelativeTime(latest);
  const statusLabel = statusRows.some((row) => row.latest_status !== "success") ? "Attention needed" : "Healthy";
  return `${sourceLabel(source)} freshness: last signal ${age}. Latest ingestion marker: ${formatDate(latestIngested || latest)}. Run status: ${statusLabel}.`;
}

function formatRelativeTime(value) {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) {
    return "time unavailable";
  }
  const diffMs = Date.now() - timestamp.getTime();
  const diffHours = Math.max(0, Math.round(diffMs / 3600000));
  if (diffHours < 1) {
    return "less than an hour ago";
  }
  if (diffHours < 24) {
    return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
  }
  const diffDays = Math.round(diffHours / 24);
  return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
}

function updateFreshnessPanel(targetId, source, timestamps) {
  const target = document.querySelector(`#${targetId}`);
  if (!target) {
    return;
  }
  target.textContent = buildFreshnessSummary(source, timestamps);
}

function downloadBlob(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function rowsToCsv(rows) {
  if (!rows.length) {
    return "no_data\n";
  }
  const keys = Object.keys(rows[0]);
  const escapeCell = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  return [
    keys.join(","),
    ...rows.map((row) => keys.map((key) => escapeCell(row[key])).join(",")),
  ].join("\n");
}

function exportRows(explorerKey, format) {
  const rows = state.explorerRows[explorerKey] || [];
  if (!rows.length) {
    document.querySelector("#ask-nasahub-response").textContent =
      `No ${sourceLabel(explorerKey)} explorer rows are loaded yet to export.`;
    return;
  }
  if (format === "json") {
    downloadBlob(`nasahub-${explorerKey}-explorer.json`, JSON.stringify(rows, null, 2), "application/json");
    return;
  }
  downloadBlob(`nasahub-${explorerKey}-explorer.csv`, rowsToCsv(rows), "text/csv;charset=utf-8");
}

function buildExplorerShareUrl(explorerKey) {
  const url = new URL(window.location.href);
  url.searchParams.set("view", "workspace");
  url.searchParams.set("workspace", explorerKey);
  if (explorerKey === "neows") {
    url.searchParams.set("neows_query", document.querySelector("#workspace-neows-query").value.trim());
  } else if (explorerKey === "eonet") {
    url.searchParams.set("eonet_category", document.querySelector("#eonet-category").value.trim());
    url.searchParams.set("eonet_status", document.querySelector("#eonet-status").value.trim());
  } else if (explorerKey === "exoplanet") {
    url.searchParams.set("exoplanet_method", document.querySelector("#exoplanet-method").value.trim());
    url.searchParams.set("exoplanet_year", document.querySelector("#exoplanet-year").value.trim());
  } else if (explorerKey === "osdr") {
    url.searchParams.set("osdr_accession", document.querySelector("#osdr-accession").value.trim());
    url.searchParams.set("osdr_source", document.querySelector("#osdr-source").value.trim());
  }
  return url.toString();
}

function buildAskShareUrl() {
  const url = new URL(window.location.href);
  url.searchParams.set("view", "workspace");
  url.searchParams.set("workspace", "ask");
  url.searchParams.set("ask_mode", askModeSelect.value);
  url.searchParams.set("ask_source", askSourceSelect.value);
  url.searchParams.set("ask_entity", askEntityInput.value.trim());
  url.searchParams.set("ask_compare", askComparisonEntityInput.value.trim());
  url.searchParams.set("ask_question", document.querySelector("#ask-question").value.trim());
  url.searchParams.set("ask_live", document.querySelector("#ask-include-live").checked ? "1" : "0");
  return url.toString();
}

async function copyTextToClipboard(value, successMessage) {
  try {
    await navigator.clipboard.writeText(value);
    document.querySelector("#ask-nasahub-response").textContent = successMessage;
  } catch (error) {
    document.querySelector("#ask-nasahub-response").textContent =
      `Clipboard copy failed. You can still use this link manually: ${value}`;
  }
}

function copyExplorerShareLink(explorerKey) {
  copyTextToClipboard(buildExplorerShareUrl(explorerKey), `${sourceLabel(explorerKey)} explorer link copied.`);
}

function copyAskShareLink() {
  copyTextToClipboard(buildAskShareUrl(), "Ask NASAHub context link copied.");
}

function exportAskResponse() {
  if (!state.lastAskResponse) {
    renderStatePanel("ask-nasahub-response", {
      eyebrow: "Nothing to export yet",
      title: "Ask NASAHub once before exporting",
      body: "The export action becomes useful after the assistant has produced one grounded answer with citations and matched records.",
      tone: "warning",
    });
    return;
  }
  downloadBlob(
    "nasahub-ask-response.json",
    JSON.stringify(state.lastAskResponse, null, 2),
    "application/json"
  );
}

function applySharedStateFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const viewerToken = params.get("access");
  if (viewerToken) {
    state.viewerMode = true;
    state.askHistory = getStoredJson(storageKey("ask_history", true), []);
    state.pins = getStoredJson(storageKey("pins", true), []);
    state.recentComparisons = getStoredJson(storageKey("recent_comparisons", true), []);
    state.savedContexts = getStoredJson(storageKey("saved_contexts", true), []);
    params.delete("access");
    const sanitized = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
    window.history.replaceState({}, "", sanitized);
  }
  if (hasCookie("nasahub_viewer_mode")) {
    state.viewerMode = true;
  }
  const view = params.get("view");
  const workspace = params.get("workspace");
  if (view) {
    state.view = view;
  }
  if (workspace) {
    state.workspaceView = workspace;
  }
  if (params.has("ask_mode")) {
    askModeSelect.value = params.get("ask_mode") || "entity";
  }
  if (params.has("ask_source")) {
    askSourceSelect.value = params.get("ask_source") || "general";
  }
  askEntityInput.value = params.get("ask_entity") || askEntityInput.value;
  askComparisonEntityInput.value = params.get("ask_compare") || askComparisonEntityInput.value;
  document.querySelector("#ask-question").value = params.get("ask_question") || document.querySelector("#ask-question").value;
  document.querySelector("#ask-include-live").checked = params.get("ask_live") === "1";
  document.querySelector("#workspace-neows-query").value = params.get("neows_query") || "";
  document.querySelector("#eonet-category").value = params.get("eonet_category") || "";
  document.querySelector("#eonet-status").value = params.get("eonet_status") || "";
  document.querySelector("#exoplanet-method").value = params.get("exoplanet_method") || "";
  document.querySelector("#exoplanet-year").value = params.get("exoplanet_year") || "";
  document.querySelector("#osdr-accession").value = params.get("osdr_accession") || "";
  document.querySelector("#osdr-source").value = params.get("osdr_source") || "";
  updateApiModeIndicator();
}

function clearAskHistory() {
  state.askHistory = [];
  localStorage.removeItem(storageKey("ask_history", state.viewerMode, state.loginRole));
  renderAskHistory();
  renderStatePanel("ask-nasahub-response", {
    eyebrow: "Conversation reset",
    title: "Ask a new grounded question when you are ready",
    body: "Use general mode for a broad ranking or explanation, or load one record and continue with a more specific comparison.",
    tone: "success",
  });
}

function updateAskModeState() {
  const isGeneral = askModeSelect.value === "general";
  askEntityInput.disabled = isGeneral;
  askComparisonEntityInput.disabled = isGeneral;
  askEntityInput.placeholder = isGeneral ? "optional in general mode" : "entity id or object name";
  askComparisonEntityInput.placeholder = isGeneral ? "disabled in general mode" : "compare with (optional)";
  if (isGeneral && !askSourceSelect.value) {
    askSourceSelect.value = "general";
  }
  if (!isGeneral && askSourceSelect.value === "general") {
    askSourceSelect.value = "neows";
  }
  renderAskOnboarding();
  renderAskSuggestions();
  renderAskContextBanner();
}

function renderAskOnboarding() {
  const mode = askModeSelect.value;
  const source = askSourceSelect.value;
  const entityId = askEntityInput.value.trim();
  const comparisonEntityId = askComparisonEntityInput.value.trim();

  if (mode === "general") {
    renderStatePanel("ask-onboarding", {
      eyebrow: "General mode",
      title: `Ask a broad question across ${source === "general" ? "all NASAHub sources" : sourceLabel(source)}`,
      body: "NASAHub is strongest when the question asks for ranking, explanation, comparison, or recent activity rather than raw database output.",
      items: [
        "Which is the biggest object that got close to Earth?",
        "What are the latest open EONET events right now?",
        "Which exoplanets in the catalog are nearest?",
      ],
      tone: "calm",
    });
    return;
  }

  if (entityId && comparisonEntityId) {
    renderStatePanel("ask-onboarding", {
      eyebrow: "Comparison mode",
      title: "You already have enough context for a useful side-by-side analysis",
      body: "Ask for the key difference, risk context, notability, or which record deserves attention first.",
      items: [
        `Compare ${entityId} and ${comparisonEntityId}`,
        "Summarize the main difference",
        "Which one matters more and why?",
      ],
      tone: "success",
    });
    return;
  }

  if (entityId) {
    renderStatePanel("ask-onboarding", {
      eyebrow: "Entity mode",
      title: `Work from the loaded ${sourceLabel(source).toLowerCase()} record`,
      body: "Ask for explanation, operational context, or what makes this record notable before branching into broader comparisons.",
      items: [
        `Summarize ${entityId}`,
        `Why does ${entityId} stand out?`,
        "What should I notice first?",
      ],
      tone: "calm",
    });
    return;
  }

  renderStatePanel("ask-onboarding", {
    eyebrow: "Getting started",
    title: "Pick a source, then either load one record or ask a broad question",
    body: "The assistant works best when the question sounds like analysis you would ask a teammate to help with.",
    items: [
      "Load a NeoWs object, EONET event, or exoplanet",
      "Or switch to general mode for cross-platform questions",
      "Use the suggested prompts just below when you want a quick start",
    ],
    tone: "calm",
  });
}

async function useCurrentEntityInAsk(source, entityId, asComparison = false) {
  if (!entityId) {
    renderStatePanel("ask-nasahub-response", {
      eyebrow: "Context needed",
      title: "Load a source record first",
      body: "Use one of the source workspaces to load a NeoWs object, EONET event, or exoplanet before sending it into Ask NASAHub.",
      tone: "warning",
    });
    return;
  }
  askModeSelect.value = "entity";
  askSourceSelect.value = source;
  if (asComparison) {
    askComparisonEntityInput.value = entityId;
  } else {
    askEntityInput.value = entityId;
    if (askComparisonEntityInput.value === entityId) {
      askComparisonEntityInput.value = "";
    }
  }
  updateAskModeState();
  setWorkspaceView("ask");
  await setDashboardView("workspace");
}

function renderAskContextBanner() {
  const target = document.querySelector("#ask-context-banner");
  const mode = askModeSelect.value;
  const source = askSourceSelect.value;
  const entityId = askEntityInput.value.trim();
  const comparisonEntityId = askComparisonEntityInput.value.trim();

  if (mode === "general") {
    target.textContent = `General mode is active for ${source === "general" ? "all sources" : source}. No fixed entity context is required.`;
    return;
  }

  if (entityId && comparisonEntityId) {
    target.innerHTML = `<strong>Comparison context</strong><br />Primary: ${escapeHtml(entityId)} | Compare with: ${escapeHtml(comparisonEntityId)} | Source: ${escapeHtml(source)}`;
    return;
  }

  if (entityId) {
    target.innerHTML = `<strong>Entity context</strong><br />Primary: ${escapeHtml(entityId)} | Source: ${escapeHtml(source)}${comparisonEntityId ? ` | Compare with: ${escapeHtml(comparisonEntityId)}` : ""}`;
    return;
  }

  target.textContent =
    "No active comparison context yet. Load a record to anchor the question, or switch to general mode for a broader search across NASAHub.";
}

function getAskSuggestions() {
  const mode = askModeSelect.value;
  const source = askSourceSelect.value;
  const entityId = askEntityInput.value.trim();
  const comparisonEntityId = askComparisonEntityInput.value.trim();

  if (mode === "entity") {
    if (entityId && comparisonEntityId) {
      if (source === "neows") {
        return [
          `Compare NeoWs objects ${entityId} and ${comparisonEntityId} on size, speed, and closest approach.`,
          `Which of ${entityId} or ${comparisonEntityId} looks riskier and why?`,
          `Summarize the main differences between ${entityId} and ${comparisonEntityId}.`,
        ];
      }
      if (source === "eonet") {
        return [
          `Compare EONET events ${entityId} and ${comparisonEntityId}.`,
          `Which of ${entityId} or ${comparisonEntityId} needs more attention and why?`,
          `Summarize the operational differences between ${entityId} and ${comparisonEntityId}.`,
        ];
      }
      return [
        `Compare exoplanets ${entityId} and ${comparisonEntityId}.`,
        `Which of ${entityId} or ${comparisonEntityId} is more notable and why?`,
        `Summarize the key scientific differences between ${entityId} and ${comparisonEntityId}.`,
      ];
    }
    if (source === "neows") {
      return [
        entityId ? `Summarize NeoWs object ${entityId}.` : "Summarize this NeoWs object.",
        entityId ? `What is the risk context for NeoWs object ${entityId}?` : "What is the risk context for this NeoWs object?",
        entityId ? `Compare local and live NASA data for ${entityId}.` : "Compare local and live NASA data for this NeoWs object.",
      ];
    }
    if (source === "eonet") {
      return [
        entityId ? `Summarize EONET event ${entityId}.` : "Summarize this EONET event.",
        entityId ? `What is the operational context for event ${entityId}?` : "What is the operational context for this event?",
        entityId ? `What should I pay attention to for event ${entityId}?` : "What should I pay attention to for this event?",
      ];
    }
    return [
      entityId ? `Summarize exoplanet ${entityId}.` : "Summarize this exoplanet.",
      entityId ? `Why is ${entityId} notable in the catalog?` : "Why is this exoplanet notable in the catalog?",
      entityId ? `Give me the discovery context for ${entityId}.` : "Give me the discovery context for this exoplanet.",
    ];
  }

  if (source === "neows") {
    return [
      "Which is the biggest object that got close to Earth?",
      "Which NeoWs objects are the fastest in the database?",
      "How many hazardous NeoWs objects were recorded recently?",
    ];
  }
  if (source === "eonet") {
    return [
      "What are the latest open events right now?",
      "Which EONET categories are the most active?",
      "What severe storm events should I review first?",
    ];
  }
  if (source === "exoplanet") {
    return [
      "Which exoplanets are nearest in our catalog?",
      "Which discovery methods dominate the catalog?",
      "Which planets were discovered most recently?",
    ];
  }
  return [
    "Which is the biggest object that got close to Earth?",
    "What are the latest open events right now?",
    "Which exoplanets are nearest in our catalog?",
  ];
}

function renderAskSuggestions() {
  const target = document.querySelector("#ask-suggestion-chips");
  const meta = document.querySelector("#ask-suggestion-meta");
  const mode = askModeSelect.value;
  const source = askSourceSelect.value;
  const suggestions = getAskSuggestions();

  meta.textContent =
    mode === "general"
      ? `Showing general prompts for ${source === "general" ? "all sources" : source}.`
      : `Showing entity prompts for ${source}.`;

  target.innerHTML = suggestions
    .map(
      (suggestion, index) => `
        <button class="suggestion-chip" type="button" data-suggestion-index="${index}">
          ${escapeHtml(suggestion)}
        </button>
      `
    )
    .join("");

  document.querySelectorAll("[data-suggestion-index]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelector("#ask-question").value = suggestions[Number(button.dataset.suggestionIndex)];
      document.querySelector("#ask-question").focus();
    });
  });
}

async function setDashboardView(view) {
  state.view = view;
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("tab-button--active", button.dataset.view === view);
  });
  document.querySelectorAll("[data-panel-group]").forEach((panel) => {
    panel.hidden = panel.dataset.panelGroup !== view;
  });
  await ensureViewLoaded(view);
  updateBreadcrumb();
}

function setWorkspaceView(view) {
  if (isGuestLogin() && view === "ask") {
    view = "neows";
  }
  state.workspaceView = view;
  document.querySelectorAll("[data-workspace-view]").forEach((button) => {
    button.classList.toggle("tab-button--active", button.dataset.workspaceView === view);
  });

  const showAsk = view === "ask";
  document.querySelectorAll("[data-workspace-panel]").forEach((panel) => {
    const panelType = panel.dataset.workspacePanel;
    panel.hidden = showAsk ? panelType !== "ask" : panelType !== "explorers";
  });
  document.querySelectorAll("[data-workspace-card]").forEach((card) => {
    card.hidden = showAsk ? true : card.dataset.workspaceCard !== view;
  });
  if (view === "neows" && !document.querySelector("#workspace-neows-table").innerHTML.trim()) {
    loadWorkspaceNeowsExplorer();
  }
  updateBreadcrumb();
}

function toggleCollapsible(targetId, button) {
  const target = document.querySelector(`#${targetId}`);
  if (!target) {
    return;
  }
  target.hidden = !target.hidden;
  button.textContent = target.hidden ? "Expand" : "Collapse";
}

function renderRelatedQuestions(targetId, questions, source) {
  const target = document.querySelector(`#${targetId}`);
  if (!target) {
    return;
  }
  if (!questions.length) {
    target.innerHTML = "";
    return;
  }
  target.innerHTML = questions
    .map(
      (question, index) => `
        <button class="suggestion-chip" type="button" data-related-question="${index}" data-related-source="${escapeHtml(source)}">
          ${escapeHtml(question)}
        </button>
      `
    )
    .join("");

  target.querySelectorAll("[data-related-question]").forEach((button) => {
    button.addEventListener("click", () => {
      prefillAskQuestion(button.dataset.relatedSource, questions[Number(button.dataset.relatedQuestion)]);
      document.querySelector("#ask-question").focus();
    });
  });
}

function bindAskEntityButtons() {
  document.querySelectorAll("[data-use-ask-source][data-use-ask-entity]").forEach((button) => {
    button.addEventListener("click", async () => {
      await useCurrentEntityInAsk(button.dataset.useAskSource, button.dataset.useAskEntity, false);
    });
  });
  document.querySelectorAll("[data-use-ask-compare][data-use-ask-entity]").forEach((button) => {
    button.addEventListener("click", async () => {
      await useCurrentEntityInAsk(button.dataset.useAskCompare, button.dataset.useAskEntity, true);
    });
  });
}

function updateBreadcrumb() {
  const target = document.querySelector("#dashboard-breadcrumb");
  const viewLabelMap = {
    overview: "Overview",
    neows: "NeoWs",
    eonet: "EONET",
    exoplanet: "Exoplanet",
    osdr: "OSDR",
    workspace: "Ask & Explore",
  };
  const crumbs = [viewLabelMap[state.view] ?? "Dashboard"];

  if (state.view === "workspace") {
    const workspaceLabelMap = {
      ask: "Assistant",
      neows: "NeoWs Explorer",
      eonet: "EONET Explorer",
      exoplanet: "Exoplanet Explorer",
      osdr: "OSDR Explorer",
    };
    crumbs.push(workspaceLabelMap[state.workspaceView] ?? "Workspace");
  }

  if (state.view === "neows" && state.currentEntities.neows) {
    crumbs.push(state.currentEntities.neows);
  } else if (state.view === "eonet" && state.currentEntities.eonet) {
    crumbs.push(state.currentEntities.eonet);
  } else if (state.view === "exoplanet" && state.currentEntities.exoplanet) {
    crumbs.push(state.currentEntities.exoplanet);
  }

  target.textContent = crumbs.join(" / ");
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
    renderStatePanel("ask-nasahub-history", {
      eyebrow: "Conversation thread",
      title: "Your grounded analysis thread will appear here",
      body: "After the first question, NASAHub will keep the recent exchange visible so follow-up questions feel more natural.",
      tone: "calm",
    });
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
  const featured = fields.filter((field) => field.featured);
  const regular = fields.filter((field) => !field.featured);
  const renderCards = (items, extraClass = "") =>
    items
      .map(
        (field) => `
          <article class="detail-card ${extraClass}">
            <div class="detail-card__label">${escapeHtml(field.label)}</div>
            <div class="detail-card__value">${field.value}</div>
          </article>
        `
      )
      .join("");

  if (!featured.length) {
    document.querySelector(`#${targetId}`).innerHTML = `<div class="detail-grid">${renderCards(regular)}</div>`;
    return;
  }

  document.querySelector(`#${targetId}`).innerHTML = `
    <div class="detail-grid-shell">
      <div class="detail-grid detail-grid--featured">${renderCards(featured, "detail-card--featured")}</div>
      <div class="detail-grid detail-grid--compact">${renderCards(regular)}</div>
    </div>
  `;
}

function renderSourceStrip(targetId, items) {
  document.querySelector(`#${targetId}`).innerHTML = items
    .map(
      (item) => `
        <article class="source-chip">
          <div class="source-chip__label">${escapeHtml(item.label)}</div>
          <div class="source-chip__value">${escapeHtml(item.value)}</div>
          <div class="source-chip__sub">${escapeHtml(item.sub)}</div>
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

function renderNeowsObjectOptions(items, targetId = "neows-object-results") {
  const select = document.querySelector(`#${targetId}`);
  const options = items
    .map(
      (item) =>
        `<option value="${escapeHtml(item.neo_reference_id)}">${escapeHtml(item.name)} [${escapeHtml(item.neo_reference_id)}]</option>`
    )
    .join("");
  select.innerHTML = `<option value="">Choose a matching object</option>${options}`;
}

function renderWorkspaceNeowsSelection(neoReferenceId) {
  document.querySelector("#workspace-neows-meta").textContent = neoReferenceId
    ? `Selected NeoWs object ${neoReferenceId}. Use it in Ask NASAHub, compare it, or open the full NeoWs detail page.`
    : "Choose a NeoWs object to continue.";
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
  renderActiveFilters(`${explorerKey}-active-filters`, filters);
}

function resetEonetExplorerFilters() {
  document.querySelector("#eonet-category").value = "";
  document.querySelector("#eonet-status").value = "";
  loadEonetExplorer();
}

function resetExoplanetExplorerFilters() {
  document.querySelector("#exoplanet-method").value = "";
  document.querySelector("#exoplanet-year").value = "";
  loadExoplanetExplorer();
}

function resetOsdrExplorerFilters() {
  document.querySelector("#osdr-accession").value = "";
  document.querySelector("#osdr-source").value = "";
  loadOsdrExplorer();
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

function renderOverviewCards({ ready, catalog, ingestion, monitor }) {
  const degradedRuns = ingestion.filter((row) => row.latest_status !== "success").length;
  const sources = new Set(catalog.endpoints.map((item) => item.source)).size;
  const monitorStatus = monitor?.overall_status || "unknown";
  const monitorLabel = monitorStatus === "ok" ? "Healthy" : monitorStatus === "degraded" ? "Attention" : "Unknown";
  const monitorSub = monitor?.checked_at_utc
    ? `Latest ops check ${formatRelativeTime(monitor.checked_at_utc)} · ${formatNumber(monitor.issue_count)} issue${monitor.issue_count === 1 ? "" : "s"}`
    : "The monitoring cron has not written a status snapshot yet.";
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
    {
      label: "Latest ops check",
      value: monitorLabel,
      sub: monitorSub,
      className: `metric-card--${monitorStatus === "ok" ? "ok" : monitorStatus === "degraded" ? "warn" : "idle"}`,
    },
  ];

  document.querySelector("#overview-cards").innerHTML = cards
    .map(
      (card) => `
        <article class="metric-card ${card.className || ""}">
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
  renderSourceStrip("neows-spotlight", [
    {
      label: "Latest day",
      value: latestDay?.close_approach_date ?? "n/a",
      sub: `${formatNumber(latestDay?.neo_count)} tracked objects`,
    },
    {
      label: "Hazardous that day",
      value: formatNumber(latestDay?.hazardous_count),
      sub: "Curated daily feed snapshot",
    },
    {
      label: "Average velocity",
      value: `${formatNumber(latestDay?.avg_velocity_km_per_hour, 0)} kph`,
      sub: "On the most recent approach day",
    },
    {
      label: "KPI records",
      value: formatNumber(kpis.length),
      sub: "Top standout objects in the current slice",
    },
  ]);
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
    <div class="chart-grid">
      <div id="neows-activity-chart"></div>
      <div id="neows-hazard-chart"></div>
    </div>
    <div class="kpi-grid">${kpiCards}</div>
  `;

  renderLineChart(
    "neows-activity-chart",
    "Daily Close Approaches",
    "Recent NeoWs activity from the curated daily summary",
    dailySummary.slice(0, 7).reverse(),
    {
      value: (row) => row.neo_count,
      label: (row) => String(row.close_approach_date).slice(5),
      legend: `<span>Total objects per recorded day</span>`,
      onClick: (row) => {
        prefillAskQuestion("neows", `Summarize NeoWs activity on ${row.close_approach_date}.`);
      },
    }
  );

  renderLineChart(
    "neows-hazard-chart",
    "Hazardous Objects Trend",
    "Hazardous count across recent close-approach days",
    dailySummary.slice(0, 7).reverse(),
    {
      value: (row) => row.hazardous_count,
      label: (row) => String(row.close_approach_date).slice(5),
      legend: `<span>Potentially hazardous objects per day</span>`,
      onClick: (row) => {
        prefillAskQuestion("neows", `How many hazardous NeoWs objects were recorded on ${row.close_approach_date}, and what stands out?`);
      },
    }
  );

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

function renderChartCard(targetId, title, subtitle, innerHtml, legendHtml = "") {
  document.querySelector(`#${targetId}`).innerHTML = `
    <article class="chart-card">
      <div class="chart-card__head">
        <div>
          <h3>${escapeHtml(title)}</h3>
          <p>${escapeHtml(subtitle)}</p>
        </div>
      </div>
      ${innerHtml}
      ${legendHtml ? `<div class="chart-legend">${legendHtml}</div>` : ""}
    </article>
  `;
}

async function openExplorerView() {
  await setDashboardView("workspace");
}

function focusExplorerCard(explorerKey) {
  setWorkspaceView(explorerKey);
  const cards = [...document.querySelectorAll(".explorer-card:not([hidden])")];
  cards.forEach((card) => card.classList.remove("explorer-card--focused"));
  const target = cards.find((card) => card.dataset.workspaceCard === explorerKey) || cards[0];
  if (!target) {
    return;
  }
  target.classList.add("explorer-card--focused");
  target.scrollIntoView({ behavior: "smooth", block: "start" });
}

function prefillAskQuestion(source, question) {
  askModeSelect.value = "general";
  askSourceSelect.value = source;
  askEntityInput.value = "";
  askComparisonEntityInput.value = "";
  document.querySelector("#ask-question").value = question;
  updateAskModeState();
  setWorkspaceView("ask");
  setDashboardView("workspace");
}

function renderActiveFilters(targetId, items) {
  const target = document.querySelector(`#${targetId}`);
  const active = items.filter(Boolean);
  if (!active.length) {
    target.innerHTML = `<span class="muted">No active filters.</span>`;
    return;
  }
  target.innerHTML = active.map((item) => `<span class="filter-pill">${escapeHtml(item)}</span>`).join("");
}

function renderLineChart(targetId, title, subtitle, rows, options) {
  if (!rows.length) {
    renderChartCard(targetId, title, subtitle, `<div class="chart-empty">No data available for this chart yet.</div>`);
    return;
  }

  const width = 640;
  const height = 280;
  const margin = { top: 20, right: 16, bottom: 42, left: 54 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const values = rows.map(options.value);
  const maxValue = Math.max(...values, 1);
  const stepX = rows.length > 1 ? innerWidth / (rows.length - 1) : innerWidth / 2;
  const points = rows.map((row, index) => {
    const x = margin.left + (rows.length > 1 ? index * stepX : innerWidth / 2);
    const y = margin.top + innerHeight - (Number(options.value(row) || 0) / maxValue) * innerHeight;
    return { x, y, row };
  });
  const linePath = points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${margin.top + innerHeight} L ${points[0].x} ${margin.top + innerHeight} Z`;
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({
    value: Math.round(maxValue * ratio),
    y: margin.top + innerHeight - ratio * innerHeight,
  }));
  const xLabels = points.filter((_, index) => index === 0 || index === rows.length - 1 || index === Math.floor((rows.length - 1) / 2));

  renderChartCard(
    targetId,
    title,
    subtitle,
    `
      <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(title)}">
        ${yTicks
          .map(
            (tick) => `
              <line class="chart-grid-line" x1="${margin.left}" y1="${tick.y}" x2="${width - margin.right}" y2="${tick.y}"></line>
              <text x="${margin.left - 10}" y="${tick.y + 4}" text-anchor="end">${escapeHtml(formatNumber(tick.value))}</text>
            `
          )
          .join("")}
        <line class="chart-axis-line" x1="${margin.left}" y1="${margin.top + innerHeight}" x2="${width - margin.right}" y2="${margin.top + innerHeight}"></line>
        <path class="chart-area" d="${areaPath}"></path>
        <path class="chart-line" d="${linePath}"></path>
        ${points
          .map(
            (point, index) => `
              <circle class="chart-point${options.onClick ? " chart-point--interactive" : ""}" cx="${point.x}" cy="${point.y}" r="5" ${options.onClick ? `data-chart-target="${escapeHtml(targetId)}" data-chart-index="${index}"` : ""}></circle>
            `
          )
          .join("")}
        ${xLabels
          .map(
            (point) => `
              <text x="${point.x}" y="${height - 10}" text-anchor="middle">${escapeHtml(options.label(point.row))}</text>
            `
          )
          .join("")}
      </svg>
    `,
    options.legend || ""
  );

  if (options.onClick) {
    document.querySelectorAll(`[data-chart-target="${targetId}"][data-chart-index]`).forEach((element) => {
      element.addEventListener("click", () => {
        const row = rows[Number(element.dataset.chartIndex)];
        options.onClick(row);
      });
    });
  }
}

function renderBarChart(targetId, title, subtitle, rows, options) {
  if (!rows.length) {
    renderChartCard(targetId, title, subtitle, `<div class="chart-empty">No data available for this chart yet.</div>`);
    return;
  }

  const width = 640;
  const height = 320;
  const margin = { top: 20, right: 16, bottom: 70, left: 54 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;
  const values = rows.map(options.value);
  const maxValue = Math.max(...values, 1);
  const barWidth = innerWidth / rows.length - 12;
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => ({
    value: Math.round(maxValue * ratio),
    y: margin.top + innerHeight - ratio * innerHeight,
  }));

  const gradientId = `${targetId}-gradient`;
  renderChartCard(
    targetId,
    title,
    subtitle,
    `
      <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(title)}">
        <defs>
          <linearGradient id="${gradientId}" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#8fdcff"></stop>
            <stop offset="100%" stop-color="#337bff"></stop>
          </linearGradient>
        </defs>
        ${yTicks
          .map(
            (tick) => `
              <line class="chart-grid-line" x1="${margin.left}" y1="${tick.y}" x2="${width - margin.right}" y2="${tick.y}"></line>
              <text x="${margin.left - 10}" y="${tick.y + 4}" text-anchor="end">${escapeHtml(formatNumber(tick.value))}</text>
            `
          )
          .join("")}
        <line class="chart-axis-line" x1="${margin.left}" y1="${margin.top + innerHeight}" x2="${width - margin.right}" y2="${margin.top + innerHeight}"></line>
        ${rows
          .map((row, index) => {
            const value = Number(options.value(row) || 0);
            const x = margin.left + index * (barWidth + 12);
            const barHeight = (value / maxValue) * innerHeight;
            const y = margin.top + innerHeight - barHeight;
            return `
              <rect class="chart-bar${options.onClick ? " chart-bar--interactive" : ""}" x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="8" fill="url(#${gradientId})" ${options.onClick ? `data-chart-target="${escapeHtml(targetId)}" data-chart-index="${index}"` : ""}></rect>
              <text x="${x + barWidth / 2}" y="${y - 8}" text-anchor="middle">${escapeHtml(formatNumber(value))}</text>
              <text x="${x + barWidth / 2}" y="${height - 26}" text-anchor="middle">${escapeHtml(options.label(row))}</text>
            `;
          })
          .join("")}
      </svg>
    `,
    options.legend || ""
  );

  if (options.onClick) {
    document.querySelectorAll(`[data-chart-target="${targetId}"][data-chart-index]`).forEach((element) => {
      element.addEventListener("click", () => {
        const row = rows[Number(element.dataset.chartIndex)];
        options.onClick(row);
      });
    });
  }
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

async function runViewLoad(view, targetIds, loader) {
  const ok = await loadSection(targetIds, loader);
  state.loadedViews[view] = ok;
  return ok;
}

async function ensureViewLoaded(view) {
  if (state.loadedViews[view]) {
    updateLastRefreshLabel();
    return;
  }

  if (view === "overview") {
    await loadOverviewView();
  } else if (view === "neows") {
    await loadNeowsView();
  } else if (view === "eonet") {
    await loadEonetView();
  } else if (view === "exoplanet") {
    await loadExoplanetView();
  } else if (view === "osdr") {
    await loadOsdrView();
  } else if (view === "workspace") {
    await loadWorkspaceView();
  }

  updateLastRefreshLabel();
}

function updateLastRefreshLabel() {
  const loadedCount = Object.values(state.loadedViews).filter(Boolean).length;
  const viewLabel = state.view === "workspace" ? "Ask & Explore" : state.view.charAt(0).toUpperCase() + state.view.slice(1);
  if (!lastRefresh) {
    return;
  }
  lastRefresh.textContent =
    loadedCount === 0
      ? "Waiting for first load..."
      : `${viewLabel} refreshed ${new Date().toLocaleString()} | ${loadedCount} workspace${loadedCount === 1 ? "" : "s"} ready`;
}

function resetViewStatuses(view) {
  if (view === "overview") {
    setSectionStatus("overview", "loading", "Loading");
    setSectionStatus("ingestion", "loading", "Loading");
    return;
  }
  setSectionStatus(view, "loading", "Loading");
}

async function refreshCurrentView() {
  state.loadedViews[state.view] = false;
  if (state.view === "workspace") {
    await ensureViewLoaded(state.view);
    return;
  }
  resetViewStatuses(state.view);
  await ensureViewLoaded(state.view);
}

async function loadWorkspaceView() {
  try {
    const [eonetCategory, exoplanetMethods, osdrSummary] = await Promise.all([
      fetchJson("/analytics/eonet/category-summary"),
      fetchJson("/analytics/exoplanet/discovery-method-summary"),
      fetchJson("/analytics/osdr/dataset-summary"),
    ]);
    populateEonetCategoryOptions(eonetCategory);
    populateExoplanetMethodOptions(exoplanetMethods);
    populateOsdrSourceOptions(osdrSummary);
    await loadPinsFromBackend();
    await loadSavedContextsFromBackend();
    state.loadedViews.workspace = true;
  } catch (error) {
    state.loadedViews.workspace = false;
    document.querySelector("#eonet-explorer-meta").textContent = "Category options unavailable right now.";
    document.querySelector("#exoplanet-explorer-meta").textContent = "Discovery method options unavailable right now.";
    document.querySelector("#osdr-explorer-meta").textContent = "OSDR source options unavailable right now.";
  }
}

async function loadOverviewView() {
  resetViewStatuses("overview");
  const ok = await runViewLoad("overview", ["overview-cards", "ingestion-status-table"], async () => {
    const [ready, catalog, ingestion, monitor] = await Promise.all([
      fetchJson("/health/ready"),
      fetchJson("/analytics/catalog"),
      fetchJson("/analytics/ingestion-status"),
      fetchJson("/analytics/monitor-status"),
    ]);
    persistIngestionStatus(ingestion);
    renderOverviewCards({ ready, catalog, ingestion, monitor });
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
  });

  if (!ok) {
    setSectionStatus("overview", "warn", "Error");
    setSectionStatus("ingestion", "warn", "Error");
  }
}

async function loadNeowsView() {
  resetViewStatuses("neows");
  const ok = await runViewLoad("neows", ["neows-summary"], async () => {
    const [neowsDaily, neowsKpis] = await Promise.all([
      fetchJson("/analytics/neows/daily-summary"),
      fetchJson("/analytics/neows/kpis"),
    ]);
    updateFreshnessPanel("neows-freshness", "neows", [
      ...neowsDaily.map((row) => row.close_approach_date),
      ...neowsKpis.map((row) => row.recent_approach_date),
    ]);
    renderNeowsSummary(neowsDaily, neowsKpis);
    setSectionStatus("neows", "ok", `${formatNumber(neowsKpis.length)} KPIs`);
    await loadNeowsObjectFinder();
    const firstObjectId = neowsKpis[0]?.object_id;
    if (firstObjectId) {
      document.querySelector("#neows-object-id").value = firstObjectId;
      await loadNeowsObjectDetail(firstObjectId);
    }
  });

  if (!ok) {
    setSectionStatus("neows", "warn", "Error");
  }
}

async function loadEonetView() {
  setSectionStatus("eonet", "loading", "Loading");
  const ok = await runViewLoad("eonet", ["eonet-summary", "eonet-explorer"], async () => {
      const [eonetCategory, eonetEvents] = await Promise.all([
        fetchJson("/analytics/eonet/category-summary"),
        fetchJson("/analytics/eonet/event-overview?limit=8&offset=0"),
      ]);
      updateFreshnessPanel("eonet-freshness", "eonet", [
        ...eonetCategory.map((row) => row.last_ingested_at),
        ...eonetEvents.items.map((row) => row.last_ingested_at),
      ]);
      const totalEvents = eonetCategory.reduce((sum, row) => sum + Number(row.total_events || 0), 0);
      const totalOpenEvents = eonetCategory.reduce((sum, row) => sum + Number(row.open_events || 0), 0);
      const topCategory = eonetCategory[0];
      renderSourceStrip("eonet-spotlight", [
        {
          label: "Categories",
          value: formatNumber(eonetCategory.length),
          sub: "Curated event categories covered",
        },
        {
          label: "Open events",
          value: formatNumber(totalOpenEvents),
          sub: "Operationally active right now",
        },
        {
          label: "Tracked events",
          value: formatNumber(totalEvents),
          sub: "Across the current category summary",
        },
        {
          label: "Top category",
          value: topCategory?.category_title ?? "n/a",
          sub: topCategory ? `${formatNumber(topCategory.total_events)} events` : "No category data yet",
        },
      ]);
      populateEonetCategoryOptions(eonetCategory);
      document.querySelector("#eonet-summary").innerHTML = `
        <div class="chart-grid">
          <div id="eonet-category-chart"></div>
          <div id="eonet-open-chart"></div>
        </div>
        <div id="eonet-bars"></div>
        <div id="eonet-events-table" class="table-wrap"></div>
      `;
      renderBarChart("eonet-category-chart", "Events By Category", "Top categories by total events", eonetCategory.slice(0, 6), {
        value: (row) => row.total_events,
        label: (row) => row.category_title.split(" ")[0],
        legend: `<span>Total events</span>`,
        onClick: (row) => {
          document.querySelector("#eonet-category").value = row.category_id;
          openExplorerView();
          focusExplorerCard("eonet");
          loadEonetExplorer();
        },
      });
      renderBarChart("eonet-open-chart", "Open Events By Category", "Operational view of currently open categories", eonetCategory.slice(0, 6), {
        value: (row) => row.open_events,
        label: (row) => row.category_title.split(" ")[0],
        legend: `<span>Open event count</span>`,
        onClick: (row) => {
          document.querySelector("#eonet-category").value = row.category_id;
          document.querySelector("#eonet-status").value = "open";
          openExplorerView();
          focusExplorerCard("eonet");
          loadEonetExplorer();
        },
      });
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
    });

  if (!ok) {
    setSectionStatus("eonet", "warn", "Error");
  }
}

async function loadExoplanetView() {
  setSectionStatus("exoplanet", "loading", "Loading");
  const ok = await runViewLoad("exoplanet", ["exoplanet-summary", "exoplanet-explorer"], async () => {
      const [exoplanetMethods, exoplanetYears, exoplanetCatalog] = await Promise.all([
        fetchJson("/analytics/exoplanet/discovery-method-summary"),
        fetchJson("/analytics/exoplanet/discovery-yearly-summary"),
        fetchJson("/analytics/exoplanet/catalog?limit=8&offset=0"),
      ]);
      updateFreshnessPanel("exoplanet-freshness", "exoplanet", [
        ...exoplanetCatalog.items.map((row) => row.last_ingested_at),
      ]);
      const topMethod = exoplanetMethods[0];
      const latestYear = exoplanetYears[0];
      renderSourceStrip("exoplanet-spotlight", [
        {
          label: "Catalog sample",
          value: formatNumber(exoplanetCatalog.total),
          sub: "Planets available through the curated endpoint",
        },
        {
          label: "Latest discovery year",
          value: latestYear?.disc_year ?? "n/a",
          sub: latestYear ? `${formatNumber(latestYear.planet_count)} planets` : "No yearly trend yet",
        },
        {
          label: "Top method",
          value: topMethod?.discovery_method ?? "n/a",
          sub: topMethod ? `${formatNumber(topMethod.planet_count)} planets` : "No method summary yet",
        },
        {
          label: "Years covered",
          value: formatNumber(exoplanetYears.length),
          sub: "Distinct discovery years in the current slice",
        },
      ]);
      populateExoplanetMethodOptions(exoplanetMethods);
      document.querySelector("#exoplanet-summary").innerHTML = `
        <div class="chart-grid">
          <div id="exo-year-chart"></div>
          <div id="exo-method-chart"></div>
        </div>
        <div id="exo-method-bars"></div>
        <div id="exo-table" class="table-wrap"></div>
      `;
      renderLineChart("exo-year-chart", "Discoveries By Year", "Curated yearly discovery trend", exoplanetYears.slice(0, 10).reverse(), {
        value: (row) => row.planet_count,
        label: (row) => String(row.disc_year),
        legend: `<span>Planet discoveries per year</span>`,
        onClick: (row) => {
          document.querySelector("#exoplanet-year").value = row.disc_year;
          openExplorerView();
          focusExplorerCard("exoplanet");
          loadExoplanetExplorer();
        },
      });
      renderBarChart("exo-method-chart", "Top Discovery Methods", "Most common methods in the current catalog", exoplanetMethods.slice(0, 6), {
        value: (row) => row.planet_count,
        label: (row) => row.discovery_method.split(" ")[0],
        legend: `<span>Planet count by discovery method</span>`,
        onClick: (row) => {
          document.querySelector("#exoplanet-method").value = row.discovery_method;
          openExplorerView();
          focusExplorerCard("exoplanet");
          loadExoplanetExplorer();
        },
      });
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
    });

  if (!ok) {
    setSectionStatus("exoplanet", "warn", "Error");
  }
}

async function loadOsdrView() {
  setSectionStatus("osdr", "loading", "Loading");
  const ok = await runViewLoad("osdr", ["osdr-summary", "osdr-explorer"], async () => {
      const [osdrSummary, osdrAssays, osdrDatasets] = await Promise.all([
        fetchJson("/analytics/osdr/dataset-summary"),
        fetchJson("/analytics/osdr/assay-type-summary"),
        fetchJson("/analytics/osdr/datasets?limit=8&offset=0"),
      ]);
      updateFreshnessPanel("osdr-freshness", "osdr", [
        ...osdrSummary.map((row) => row.last_ingested_at),
        ...osdrDatasets.items.map((row) => row.last_ingested_at),
      ]);
      const totalFiles = osdrSummary.reduce((sum, row) => sum + Number(row.file_count || 0), 0);
      const topDataset = osdrSummary[0];
      const topAssay = osdrAssays[0];
      renderSourceStrip("osdr-spotlight", [
        {
          label: "Datasets",
          value: formatNumber(osdrSummary.length),
          sub: "Curated operational dataset rollups",
        },
        {
          label: "Files tracked",
          value: formatNumber(totalFiles),
          sub: "Across the dataset summary slice",
        },
        {
          label: "Largest dataset",
          value: topDataset?.dataset_accession ?? "n/a",
          sub: topDataset ? `${formatNumber(topDataset.file_count)} files` : "No dataset summary yet",
        },
        {
          label: "Top assay type",
          value: topAssay?.assay_type ?? "n/a",
          sub: topAssay ? `${formatNumber(topAssay.assay_count)} assays` : "No assay summary yet",
        },
      ]);
      populateOsdrSourceOptions(osdrSummary);
      document.querySelector("#osdr-summary").innerHTML = `
        <div class="chart-grid">
          <div id="osdr-dataset-chart"></div>
          <div id="osdr-assay-chart"></div>
        </div>
        <div id="osdr-dataset-table" class="table-wrap"></div>
        <div id="osdr-assay-bars"></div>
      `;
      renderBarChart("osdr-dataset-chart", "Dataset File Volume", "Top datasets by file count", osdrSummary.slice(0, 6), {
        value: (row) => row.file_count,
        label: (row) => row.dataset_accession,
        legend: `<span>Files per dataset</span>`,
        onClick: (row) => {
          document.querySelector("#osdr-accession").value = row.dataset_accession;
          openExplorerView();
          focusExplorerCard("osdr");
          loadOsdrExplorer();
        },
      });
      renderBarChart("osdr-assay-chart", "Assay Type Distribution", "Most common assay types in the current OSDR slice", osdrAssays.slice(0, 6), {
        value: (row) => row.assay_count,
        label: (row) => row.assay_type === "Unknown" ? "Unknown" : row.assay_type.split(" ")[0],
        legend: `<span>Assays per assay type</span>`,
        onClick: (row) => {
          prefillAskQuestion("general", `What does the OSDR assay type "${row.assay_type}" represent in the current dataset slice?`);
        },
      });
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
          {
            key: "dataset_accession",
            label: "Dataset",
            render: (row) => escapeHtml(row.dataset_accession),
          },
          {
            key: "actions",
            label: "Watch",
            render: (row) => `
              <div class="inline-fields">
                <button class="button" type="button" data-pin-osdr="${escapeHtml(row.dataset_accession)}">Pin</button>
              </div>
            `,
          },
          { key: "dataset_label", label: "Label" },
          { key: "last_ingested_at", label: "Ingested", render: (row) => escapeHtml(formatDate(row.last_ingested_at)) },
        ],
        osdrDatasets.items
      );
      state.explorerRows.osdr = osdrDatasets.items;
      bindOsdrPinButtons();
      state.explorers.osdr.offset = 0;
      state.explorers.osdr.limit = 8;
      renderExplorerMeta("osdr", osdrDatasets);
      setSectionStatus("osdr", "ok", `${formatNumber(osdrSummary.length)} datasets`);
  });

  if (!ok) {
    setSectionStatus("osdr", "warn", "Error");
  }
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

async function loadWorkspaceNeowsExplorer() {
  const query = document.querySelector("#workspace-neows-query").value.trim();
  const metaId = "workspace-neows-meta";
  document.querySelector(`#${metaId}`).textContent = query
    ? `Searching NeoWs objects for "${query}"...`
    : "Loading NeoWs object suggestions...";
  setLoading("workspace-neows-table");
  try {
    const params = new URLSearchParams({ limit: "12" });
    if (query) {
      params.set("query", query);
    }
    const items = await fetchJson(`/analytics/neows/objects?${params.toString()}`);
    state.explorerRows.neows = items;
    renderNeowsObjectOptions(items, "workspace-neows-results");
    renderTable(
      "workspace-neows-table",
      [
        {
          key: "neo_reference_id",
          label: "Object",
          render: (row) =>
            `<button class="button" type="button" data-workspace-neows="${escapeHtml(row.neo_reference_id)}">${escapeHtml(row.name)} [${escapeHtml(row.neo_reference_id)}]</button>`,
        },
        {
          key: "is_potentially_hazardous_asteroid",
          label: "Hazardous",
          render: (row) => escapeHtml(row.is_potentially_hazardous_asteroid ? "yes" : "no"),
        },
        {
          key: "most_recent_close_approach_date",
          label: "Recent approach",
          render: (row) => escapeHtml(row.most_recent_close_approach_date ?? "n/a"),
        },
        {
          key: "approach_count",
          label: "Approaches",
          render: (row) => formatNumber(row.approach_count),
        },
        {
          key: "actions",
          label: "Ask",
          render: (row) => `
            <div class="inline-fields">
              <button class="button" type="button" data-use-ask-source="neows" data-use-ask-entity="${escapeHtml(row.neo_reference_id)}">Use</button>
              <button class="button" type="button" data-use-ask-compare="neows" data-use-ask-entity="${escapeHtml(row.neo_reference_id)}">Compare</button>
            </div>
          `,
        },
      ],
      items
    );
    document.querySelectorAll("[data-workspace-neows]").forEach((button) => {
      button.addEventListener("click", () => {
        const neoReferenceId = button.dataset.workspaceNeows;
        document.querySelector("#workspace-neows-results").value = neoReferenceId;
        renderWorkspaceNeowsSelection(neoReferenceId);
      });
    });
    bindAskEntityButtons();
    if (!items.length) {
      document.querySelector(`#${metaId}`).textContent = "No matching NeoWs objects found.";
      return;
    }
    document.querySelector(`#${metaId}`).textContent = query
      ? `${formatNumber(items.length)} matching NeoWs objects found.`
      : `Showing ${formatNumber(items.length)} NeoWs object suggestions.`;
  } catch (error) {
    renderNeowsObjectOptions([], "workspace-neows-results");
    renderError("workspace-neows-table", error.message);
    document.querySelector(`#${metaId}`).textContent = "NeoWs workspace search unavailable right now.";
  }
}

async function loadNeowsObjectDetail(neoReferenceId) {
  const targetId = "neows-object-detail";
  const metaId = "neows-object-meta";
  if (!neoReferenceId) {
    state.currentEntities.neows = "";
    document.querySelector(`#${metaId}`).textContent =
      "Search for a NeoWs object or use one of the KPI cards to open a focused object workspace.";
    renderRelatedQuestions("neows-related-questions", [], "neows");
    updateBreadcrumb();
    renderStatePanel("neows-detail-guide", {
      eyebrow: "NeoWs workspace",
      title: "Load one object and work outward",
      body: "Search for a NeoWs object, inspect its local summary, then layer on live NASA enrichment, close approaches, and Ask NASAHub comparisons.",
      tone: "calm",
    });
    renderStatePanel("neows-object-summary", {
      eyebrow: "Local summary",
      title: "No NeoWs object loaded yet",
      body: "Once one object is selected, NASAHub will turn the raw fields into a short grounded reading of what matters first.",
      tone: "calm",
    });
    renderStatePanel("neows-live-enrichment", {
      eyebrow: "Live enrichment",
      title: "No live NASA comparison yet",
      body: "After an object is loaded, you can bring in the live NASA view and compare it with NASAHub’s curated local profile.",
      tone: "calm",
    });
    renderStatePanel("neows-copilot", {
      eyebrow: "NeoWs copilot",
      title: "Contextual guidance starts after one object is loaded",
      body: "The copilot can then explain the object, frame the risk context, or compare local and live perspectives.",
      tone: "calm",
    });
    document.querySelector("#neows-approach-meta").textContent =
      "Load a NeoWs object to see its recorded close approaches.";
    renderStatePanel("neows-approach-table", {
      eyebrow: "Approach history",
      title: "No object loaded yet",
      body: "This table becomes useful once one object is in focus, especially for comparing how often it appears and how close it gets.",
      tone: "calm",
    });
    renderStatePanel(targetId, {
      eyebrow: "NeoWs detail",
      title: "No object loaded yet",
      body: "Start with one object to open its detail profile, local summary, copilot actions, and approach history in one screen.",
      tone: "calm",
    });
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
    state.currentEntities.neows = payload.name || payload.neo_reference_id;
    state.neowsApproaches.currentObjectId = neoReferenceId;
    state.neowsApproaches.offset = 0;
    askModeSelect.value = "entity";
    askSourceSelect.value = "neows";
    askEntityInput.value = payload.neo_reference_id;
    updateAskModeState();
    updateBreadcrumb();
    renderStatePanel("neows-detail-guide", {
      eyebrow: "NeoWs object loaded",
      title: payload.name,
      body: `This workspace is now centered on ${payload.neo_reference_id}. Use the local summary first, then branch into live NASA enrichment, approach history, or Ask NASAHub comparisons.`,
      items: [
        payload.is_potentially_hazardous_asteroid ? "Potentially hazardous" : "Not flagged as hazardous",
        `${formatNumber(payload.approach_count)} recorded approach(es)`,
        payload.most_recent_close_approach_date ? `Latest approach ${payload.most_recent_close_approach_date}` : "Latest approach timing available in the detail cards",
      ],
      tone: "success",
    });
    document.querySelector(`#${metaId}`).textContent =
      `${payload.name} | ${payload.approach_count} recorded approaches | latest ${payload.most_recent_close_approach_date ?? "n/a"}`;
    renderRelatedQuestions(
      "neows-related-questions",
      [
        `Summarize NeoWs object ${payload.neo_reference_id}.`,
        `What is the risk context for NeoWs object ${payload.neo_reference_id}?`,
        `Compare local and live NASA data for ${payload.neo_reference_id}.`,
      ],
      "neows"
    );
    document.querySelector("#neows-object-summary").textContent = buildNeowsObjectSummary(payload);
    renderDetailGrid(targetId, [
      { label: "Reference ID", value: escapeHtml(payload.neo_reference_id), featured: true },
      { label: "Hazardous", value: escapeHtml(payload.is_potentially_hazardous_asteroid ? "yes" : "no"), featured: true },
      { label: "Recent approach", value: escapeHtml(payload.most_recent_close_approach_date ?? "n/a"), featured: true },
      { label: "Closest miss (km)", value: escapeHtml(formatNumber(payload.min_miss_distance_km, 0)), featured: true },
      { label: "Sentry object", value: escapeHtml(payload.is_sentry_object ? "yes" : "no") },
      { label: "Absolute magnitude", value: escapeHtml(formatNumber(payload.absolute_magnitude_h, 2)) },
      { label: "Diameter min (km)", value: escapeHtml(formatNumber(payload.estimated_diameter_min_km, 3)) },
      { label: "Diameter max (km)", value: escapeHtml(formatNumber(payload.estimated_diameter_max_km, 3)) },
      { label: "First approach", value: escapeHtml(payload.first_close_approach_date ?? "n/a") },
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
    state.currentEntities.neows = "";
    updateBreadcrumb();
    document.querySelector(`#${metaId}`).textContent = "NeoWs object detail unavailable";
    renderStatePanel("neows-object-summary", {
      eyebrow: "NeoWs detail unavailable",
      title: "NASAHub could not build the local object summary",
      body: `The object detail request failed, so the summary could not be prepared: ${error.message}`,
      tone: "warning",
    });
    renderStatePanel("neows-copilot", {
      eyebrow: "NeoWs copilot unavailable",
      title: "The contextual guidance lane could not start",
      body: `The object detail request failed, so the NeoWs copilot is unavailable right now: ${error.message}`,
      tone: "warning",
    });
    renderError(targetId, error.message);
  }
}

async function loadNeowsLiveEnrichment(neoReferenceId) {
  const target = document.querySelector("#neows-live-enrichment");
  if (!neoReferenceId) {
    renderStatePanel("neows-live-enrichment", {
      eyebrow: "Live enrichment",
      title: "Load a NeoWs object first",
      body: "Once an object is loaded, you can compare NASAHub’s local summary with a live NASA lookup.",
      tone: "calm",
    });
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
    renderStatePanel("neows-live-enrichment", {
      eyebrow: "Live enrichment unavailable",
      title: "NASA live lookup could not complete",
      body: `NASAHub still has the local curated object profile, but the live NASA step failed: ${error.message}`,
      tone: "warning",
    });
  }
}

async function loadNeowsApproaches() {
  const targetId = "neows-approach-table";
  const neoReferenceId = state.neowsApproaches.currentObjectId;
  if (!neoReferenceId) {
    document.querySelector("#neows-approach-meta").textContent =
      "Load a NeoWs object to see its recorded close approaches.";
    renderStatePanel(targetId, {
      eyebrow: "Approach history",
      title: "No object loaded yet",
      body: "This table becomes useful once one object is in focus, especially for comparing how often it appears and how close it gets.",
      tone: "calm",
    });
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
    renderStatePanel("neows-copilot", {
      eyebrow: "NeoWs copilot",
      title: "Load a NeoWs object first",
      body: "Then you can ask for explanation, risk context, or a local-versus-live comparison without typing the context manually.",
      tone: "calm",
    });
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
    renderStatePanel("neows-copilot", {
      eyebrow: "NeoWs copilot unavailable",
      title: "The contextual guidance step failed",
      body: `NASAHub could not generate the NeoWs insight right now: ${error.message}`,
      tone: "warning",
    });
  }
}

async function loadEonetDetail(eventId) {
  const targetId = "eonet-detail";
  const metaId = "eonet-detail-meta";
  if (!eventId) {
    state.currentEntities.eonet = "";
    document.querySelector(`#${metaId}`).textContent = "Load an EONET event to open its focused detail workspace.";
    renderRelatedQuestions("eonet-related-questions", [], "eonet");
    updateBreadcrumb();
    renderStatePanel("eonet-insight", {
      eyebrow: "EONET guidance",
      title: "Load one event to activate the guidance lane",
      body: "Once an event is loaded, NASAHub can summarize the operational context and suggest what deserves attention next.",
      tone: "calm",
    });
    renderStatePanel(targetId, {
      eyebrow: "EONET detail",
      title: "No event loaded yet",
      body: "Start with one event to see its status, categories, source links, and follow-up questions in one place.",
      tone: "calm",
    });
    return;
  }

  setLoading(targetId);
  document.querySelector(`#${metaId}`).textContent = `Loading ${eventId}...`;
  try {
    const payload = await fetchJson(`/analytics/eonet/event/${encodeURIComponent(eventId)}`);
    state.currentEntities.eonet = payload.event_id;
    document.querySelector("#eonet-event-id").value = payload.event_id;
    askModeSelect.value = "entity";
    askSourceSelect.value = "eonet";
    askEntityInput.value = payload.event_id;
    updateAskModeState();
    updateBreadcrumb();
    renderStatePanel("eonet-detail-guide", {
      eyebrow: "EONET event loaded",
      title: payload.title,
      body: `This workspace is now centered on ${payload.event_id}. Use the guidance lane for operational interpretation or send the event into Ask NASAHub for deeper explanation.`,
      items: [
        `${payload.event_status} status`,
        `${formatNumber(payload.geometry_count)} geometry update(s)`,
        payload.category_titles || "Category context available in the detail cards",
      ],
      tone: "success",
    });
    document.querySelector(`#${metaId}`).textContent =
      `${payload.title} | ${payload.event_status} | ${payload.geometry_count} geometry update(s)`;
    renderRelatedQuestions(
      "eonet-related-questions",
      [
        `Summarize EONET event ${payload.event_id}.`,
        `What is the operational context for event ${payload.event_id}?`,
        `What should I pay attention to for event ${payload.event_id}?`,
      ],
      "eonet"
    );
    renderDetailGrid(targetId, [
      { label: "Event ID", value: escapeHtml(payload.event_id), featured: true },
      { label: "Status", value: escapeHtml(payload.event_status), featured: true },
      { label: "Latest activity", value: escapeHtml(formatDate(payload.latest_geometry_at)), featured: true },
      { label: "Geometry count", value: escapeHtml(formatNumber(payload.geometry_count)), featured: true },
      { label: "Categories", value: escapeHtml(payload.category_titles ?? "n/a") },
      { label: "Sources", value: escapeHtml(payload.source_titles ?? "n/a") },
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
    state.currentEntities.eonet = "";
    updateBreadcrumb();
    document.querySelector(`#${metaId}`).textContent = "EONET event detail unavailable";
    renderStatePanel("eonet-insight", {
      eyebrow: "EONET guidance unavailable",
      title: "The guidance lane could not start",
      body: `NASAHub could not build the EONET interpretation for this event because the detail request failed: ${error.message}`,
      tone: "warning",
    });
    renderError(targetId, error.message);
  }
}

async function loadEonetInsight(eventId, mode) {
  const target = document.querySelector("#eonet-insight");
  if (!eventId) {
    renderStatePanel("eonet-insight", {
      eyebrow: "EONET guidance",
      title: "Load an EONET event first",
      body: "Then this area can summarize the event, frame the operational context, or highlight what to pay attention to next.",
      tone: "calm",
    });
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
    renderStatePanel("eonet-insight", {
      eyebrow: "EONET guidance unavailable",
      title: "The guidance request failed",
      body: `NASAHub could not generate the EONET guidance right now: ${error.message}`,
      tone: "warning",
    });
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
    state.currentEntities.exoplanet = "";
    document.querySelector(`#${metaId}`).textContent = "Load an exoplanet to open its focused discovery workspace.";
    renderRelatedQuestions("exoplanet-related-questions", [], "exoplanet");
    updateBreadcrumb();
    renderStatePanel("exoplanet-insight", {
      eyebrow: "Exoplanet guidance",
      title: "Load a planet to activate the guidance lane",
      body: "Once a planet is loaded, NASAHub can explain the discovery context, notability, and comparison opportunities.",
      tone: "calm",
    });
    renderStatePanel(targetId, {
      eyebrow: "Exoplanet detail",
      title: "No planet loaded yet",
      body: "Start with one planet to see its discovery profile, host context, and follow-up questions in one place.",
      tone: "calm",
    });
    return;
  }

  setLoading(targetId);
  document.querySelector(`#${metaId}`).textContent = `Loading ${plName}...`;
  try {
    const payload = await fetchJson(`/analytics/exoplanet/planet/${encodeURIComponent(plName)}`);
    state.currentEntities.exoplanet = payload.pl_name;
    document.querySelector("#exoplanet-planet-name").value = payload.pl_name;
    askModeSelect.value = "entity";
    askSourceSelect.value = "exoplanet";
    askEntityInput.value = payload.pl_name;
    updateAskModeState();
    updateBreadcrumb();
    renderStatePanel("exoplanet-detail-guide", {
      eyebrow: "Exoplanet loaded",
      title: payload.pl_name,
      body: `This workspace is now centered on ${payload.pl_name}. Use the guidance lane for scientific context or send the planet into Ask NASAHub for deeper comparison.`,
      items: [
        payload.discovery_method,
        payload.hostname || "Host star context available",
        payload.disc_year ? `Discovered in ${payload.disc_year}` : "Discovery year available in the detail cards",
      ],
      tone: "success",
    });
    document.querySelector(`#${metaId}`).textContent =
      `${payload.pl_name} | ${payload.discovery_method} | ${payload.hostname ?? "host unknown"}`;
    renderRelatedQuestions(
      "exoplanet-related-questions",
      [
        `Summarize exoplanet ${payload.pl_name}.`,
        `Give me the discovery context for ${payload.pl_name}.`,
        `Why is ${payload.pl_name} notable in the catalog?`,
      ],
      "exoplanet"
    );
    renderDetailGrid(targetId, [
      { label: "Planet", value: escapeHtml(payload.pl_name), featured: true },
      { label: "Host star", value: escapeHtml(payload.hostname ?? "n/a"), featured: true },
      { label: "Discovery method", value: escapeHtml(payload.discovery_method), featured: true },
      { label: "Discovery year", value: escapeHtml(payload.disc_year ?? "n/a"), featured: true },
      { label: "Distance (pc)", value: escapeHtml(formatNumber(payload.sy_dist, 2)) },
      { label: "Orbital period (days)", value: escapeHtml(formatNumber(payload.pl_orbper, 2)) },
      { label: "Radius", value: escapeHtml(formatNumber(payload.pl_rade, 2)) },
      { label: "Mass", value: escapeHtml(formatNumber(payload.pl_bmasse, 2)) },
      { label: "Host temp", value: escapeHtml(formatNumber(payload.st_teff, 0)) },
      { label: "Last ingested", value: escapeHtml(formatDate(payload.last_ingested_at)) },
    ]);
    await loadExoplanetInsight(payload.pl_name, "overview");
  } catch (error) {
    state.currentEntities.exoplanet = "";
    updateBreadcrumb();
    document.querySelector(`#${metaId}`).textContent = "Exoplanet detail unavailable";
    renderStatePanel("exoplanet-insight", {
      eyebrow: "Exoplanet guidance unavailable",
      title: "The guidance lane could not start",
      body: `NASAHub could not build the exoplanet interpretation because the detail request failed: ${error.message}`,
      tone: "warning",
    });
    renderError(targetId, error.message);
  }
}

async function loadExoplanetInsight(plName, mode) {
  const target = document.querySelector("#exoplanet-insight");
  if (!plName) {
    renderStatePanel("exoplanet-insight", {
      eyebrow: "Exoplanet guidance",
      title: "Load an exoplanet first",
      body: "Then this area can explain discovery context, scientific notability, or comparison framing for the selected planet.",
      tone: "calm",
    });
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
    renderStatePanel("exoplanet-insight", {
      eyebrow: "Exoplanet guidance unavailable",
      title: "The guidance request failed",
      body: `NASAHub could not generate the exoplanet guidance right now: ${error.message}`,
      tone: "warning",
    });
  }
}

async function loadAskNasaHub() {
  if (isGuestLogin()) {
    renderStatePanel("ask-nasahub-response", {
      eyebrow: "Guest access",
      title: "Ask NASAHub is locked for guest",
      body: "Sign in with a user or admin account to use the chatbot.",
      tone: "warning",
    });
    return;
  }

  const mode = askModeSelect.value;
  const source = askSourceSelect.value;
  const entityId = askEntityInput.value.trim();
  const comparisonEntityId = askComparisonEntityInput.value.trim();
  const question = document.querySelector("#ask-question").value.trim();
  const includeLive = document.querySelector("#ask-include-live").checked;
  const target = document.querySelector("#ask-nasahub-response");

  if (!question) {
    renderStatePanel("ask-nasahub-response", {
      eyebrow: "Question needed",
      title: "Write a question first",
      body: "A good start is a ranking, comparison, explanation, or operational summary over the selected source or across NASAHub.",
      tone: "warning",
    });
    return;
  }

  if (mode === "entity" && !entityId) {
    renderStatePanel("ask-nasahub-response", {
      eyebrow: "Entity required",
      title: "Entity mode needs one selected record",
      body: "Load a NeoWs object, EONET event, or exoplanet first, or switch to general mode for a broader question.",
      tone: "warning",
    });
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
        comparison_entity_id: mode === "entity" && comparisonEntityId ? comparisonEntityId : null,
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
    state.lastAskResponse = payload;
    state.askHistory = payload.conversation ?? [
      ...history,
      { role: "user", content: question },
      { role: "assistant", content: payload.answer },
    ];
    persistAskHistory();
    if (payload.mode === "entity" && payload.comparison_entity_id) {
      rememberRecentComparison(
        payload.source,
        payload.entity_id ?? entityId,
        payload.comparison_entity_id,
        question
      );
    }
    renderAskHistory();
    target.innerHTML = `
      <strong>Ask NASAHub</strong><br />
      <span class="muted">Mode:</span> ${escapeHtml(payload.mode)}<br />
      <span class="muted">Resolved source:</span> ${escapeHtml(payload.source)}<br />
      <span class="muted">Entity:</span> ${escapeHtml(payload.entity_id ?? "not required")}<br /><br />
      <span class="muted">Compare with:</span> ${escapeHtml(payload.comparison_entity_id ?? "not used")}<br /><br />
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
      state.explorerRows.eonet = payload.items;
      renderTable(
        "eonet-explorer",
        [
          {
            key: "event_id",
            label: "Event",
            render: (row) =>
              `<button class="button" type="button" data-eonet-event="${escapeHtml(row.event_id)}">${escapeHtml(row.event_id)}</button>`,
          },
          {
            key: "actions",
            label: "Ask",
            render: (row) => `
              <div class="inline-fields">
                <button class="button" type="button" data-use-ask-source="eonet" data-use-ask-entity="${escapeHtml(row.event_id)}">Use</button>
                <button class="button" type="button" data-use-ask-compare="eonet" data-use-ask-entity="${escapeHtml(row.event_id)}">Compare</button>
              </div>
            `,
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
    bindAskEntityButtons();
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
      state.explorerRows.exoplanet = payload.items;
      renderTable(
        "exoplanet-explorer",
        [
          {
            key: "pl_name",
            label: "Planet",
            render: (row) =>
              `<button class="button" type="button" data-exoplanet-planet="${escapeHtml(row.pl_name)}">${escapeHtml(row.pl_name)}</button>`,
          },
          {
            key: "actions",
            label: "Ask",
            render: (row) => `
              <div class="inline-fields">
                <button class="button" type="button" data-use-ask-source="exoplanet" data-use-ask-entity="${escapeHtml(row.pl_name)}">Use</button>
                <button class="button" type="button" data-use-ask-compare="exoplanet" data-use-ask-entity="${escapeHtml(row.pl_name)}">Compare</button>
              </div>
            `,
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
    bindAskEntityButtons();
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
    state.explorerRows.osdr = payload.items;
    renderTable(
      "osdr-explorer",
      [
        {
          key: "dataset_accession",
          label: "Dataset",
          render: (row) => escapeHtml(row.dataset_accession),
        },
        {
          key: "actions",
          label: "Watch",
          render: (row) => `
            <div class="inline-fields">
              <button class="button" type="button" data-pin-osdr="${escapeHtml(row.dataset_accession)}">Pin</button>
            </div>
          `,
        },
        { key: "dataset_label", label: "Label" },
        { key: "last_ingested_at", label: "Ingested", render: (row) => escapeHtml(formatDate(row.last_ingested_at)) },
        ],
      payload.items
    );
    bindOsdrPinButtons();
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

setWorkspaceView(state.workspaceView);
setDashboardView(state.view);
