const appConfig = {
  githubRepo: "",
  githubLabels: [],
  issueTitlePrefix: "[Atlas feedback]",
  sourceManifestPath: "",
  showLocalSourceLinks: false,
  assetVersion: "20260607-github-prep",
  ...(window.FILAMENT_ATLAS_CONFIG || {}),
};

const state = {
  data: null,
  materials: [],
  filtered: [],
  selectedId: null,
  pinned: [],
  sourceIndex: new Map(),
  detailView: "properties",
  advanced: false,
  radarZoom: 1,
  radarSelectedKeys: [],
  mapZoom: 1,
  mapCenter: null,
  mapPan: null,
  mapKeys: { x: "", y: "" },
  feedbackContext: null,
  tableSort: { key: "", direction: "asc" },
};

const heroMetricKeys = [
  "hdt",
  "tensile_strength",
  "tensile_modulus",
  "elongation",
  "density",
  "nozzle_temperature",
];

const fingerprintDefs = [
  { key: "tensile_strength", label: "Strength", fallback: 0.5 },
  { key: "tensile_modulus", label: "Stiffness", fallback: 0.5 },
  { key: "elongation", label: "Ductility", fallback: 0.42 },
  { key: "hdt", label: "Heat", fallback: 0.45 },
  { key: "printability", label: "Print ease", fallback: 0.62 },
];

const thermalKeys = [
  "nozzle_temperature",
  "bed_temperature",
  "chamber_temperature",
  "drying_temperature",
  "annealing_temperature",
];

const radarAxes = [
  "tensile_strength",
  "tensile_modulus",
  "elongation",
  "flexural_strength",
  "flexural_modulus",
  "impact_strength",
  "impact_charpy",
  "hdt",
  "glass_transition",
  "density",
];

const requestedBasicPropertyKeys = [
  "density",
  "nozzle_temperature",
  "bed_temperature",
  "chamber_temperature",
  "hdt",
  "impact_best",
  "tensile_strength::xy",
  "tensile_strength::z",
  "tensile_modulus::xy",
  "tensile_modulus::z",
  "flexural_modulus::xy",
  "flexural_modulus::z",
];

const directionalPropertyKeys = new Set([
  "tensile_strength",
  "tensile_modulus",
  "flexural_strength",
  "flexural_modulus",
  "impact_strength",
  "impact_charpy",
  "impact_izod_area",
]);

const basePalette = {
  ABS: [18, 76],
  ASA: [33, 78],
  CPE: [184, 62],
  HIPS: [48, 64],
  PA: [257, 58],
  PA11: [270, 57],
  PA12: [282, 58],
  PA6: [248, 60],
  PA612: [294, 56],
  PAHT: [232, 60],
  PC: [219, 68],
  PCTG: [193, 65],
  PEEK: [354, 70],
  PEI: [329, 65],
  PEKK: [342, 68],
  PET: [205, 69],
  PETG: [199, 69],
  PLA: [154, 64],
  PP: [111, 56],
  PPA: [236, 56],
  PPS: [6, 67],
  PPSU: [16, 62],
  PSU: [27, 62],
  PVA: [176, 55],
  PVB: [168, 58],
  PVDF: [290, 58],
  TPU: [305, 62],
  ULTEM: [329, 65],
  UNKNOWN: [45, 8],
};

const els = {
  summaryText: document.getElementById("summaryText"),
  generatedDate: document.getElementById("generatedDate"),
  searchInput: document.getElementById("searchInput"),
  supplierFilter: document.getElementById("supplierFilter"),
  baseFilter: document.getElementById("baseFilter"),
  familyFilter: document.getElementById("familyFilter"),
  propertyFilter: document.getElementById("propertyFilter"),
  parsedOnly: document.getElementById("parsedOnly"),
  resetFilters: document.getElementById("resetFilters"),
  clearFilters: document.getElementById("clearFilters"),
  themeToggle: document.getElementById("themeToggle"),
  corpusStats: document.getElementById("corpusStats"),
  baseLegend: document.getElementById("baseLegend"),
  baseCount: document.getElementById("baseCount"),
  generatedDateFooter: document.getElementById("generatedDateFooter"),
  kpiCards: document.getElementById("kpiCards"),
  selectedSummary: document.getElementById("selectedSummary"),
  resultCount: document.getElementById("resultCount"),
  materialsBody: document.getElementById("materialsBody"),
  detailHero: document.getElementById("detailHero"),
  propertyChips: document.getElementById("propertyChips"),
  heroMetrics: document.getElementById("heroMetrics"),
  fingerprintPanel: document.getElementById("fingerprintPanel"),
  thermalPanel: document.getElementById("thermalPanel"),
  advancedToggle: document.getElementById("advancedToggle"),
  detailProperties: document.getElementById("detailProperties"),
  sourcePanel: document.getElementById("sourcePanel"),
  pinCount: document.getElementById("pinCount"),
  pinTray: document.getElementById("pinTray"),
  compareMatrix: document.getElementById("compareMatrix"),
  familyBaseSelect: document.getElementById("familyBaseSelect"),
  familySummary: document.getElementById("familySummary"),
  familyStats: document.getElementById("familyStats"),
  mapX: document.getElementById("mapX"),
  mapY: document.getElementById("mapY"),
  mapColorBy: document.getElementById("mapColorBy"),
  mapZoomLabel: document.getElementById("mapZoomLabel"),
  resetMapZoom: document.getElementById("resetMapZoom"),
  materialMap: document.getElementById("materialMap"),
  feedbackModal: document.getElementById("feedbackModal"),
  feedbackForm: document.getElementById("feedbackForm"),
  feedbackContext: document.getElementById("feedbackContext"),
  feedbackText: document.getElementById("feedbackText"),
  feedbackClose: document.getElementById("feedbackClose"),
  feedbackExport: document.getElementById("feedbackExport"),
  feedbackSubmit: document.getElementById("feedbackSubmit"),
  spreadMode: document.getElementById("spreadMode"),
  spreadHint: document.getElementById("spreadHint"),
  spreadRows: document.getElementById("spreadRows"),
  radarA: document.getElementById("radarA"),
  radarB: document.getElementById("radarB"),
  radarGroup: document.getElementById("radarGroup"),
  radarAxes: document.getElementById("radarAxes"),
  radarChart: document.getElementById("radarChart"),
  radarLegend: document.getElementById("radarLegend"),
  radarZoomLabel: document.getElementById("radarZoomLabel"),
  tooltip: document.getElementById("tooltip"),
};

function withAssetVersion(path) {
  const version = appConfig.assetVersion || "";
  if (!version) return path;
  return `${path}${path.includes("?") ? "&" : "?"}v=${encodeURIComponent(version)}`;
}

initTheme();
initTooltip();
initFeedback();

Promise.allSettled([
  fetch(withAssetVersion("data/materials.json")).then((r) => {
    if (!r.ok) throw new Error(`materials.json returned ${r.status}`);
    return r.json();
  }),
  loadManifestSources(),
])
  .then(([dataResult, sourcesResult]) => {
    if (dataResult.status !== "fulfilled") throw dataResult.reason;
    state.data = dataResult.value;
    state.materials = state.data.materials || [];
    state.sourceIndex = sourcesResult.status === "fulfilled" ? sourcesResult.value : new Map();
    initControls();
    applyFilters();
    selectFirstParsed();
    renderRadar();
    requestAnimationFrame(scrollToHash);
    window.setTimeout(scrollToHash, 350);
    refreshIcons();
  })
  .catch((err) => {
    els.summaryText.textContent = `Could not load database: ${err.message}`;
  });

function formatUnit(unit) {
  const labels = {
    degC: "°C",
    degF: "°F",
    "g/cm3": "g/cm³",
    "kg/m3": "kg/m³",
    "g/cc": "g/cc",
    "g/10min": "g/10 min",
    "cm3/10min": "cm³/10 min",
    "mm3/s": "mm³/s",
    "kJ/m2": "kJ/m²",
    "J/m2": "J/m²",
    "ft-lb/in": "ft-lb/in",
    ohm: "Ω",
    "ohm/sq": "Ω/sq",
  };
  return labels[unit] || unit || "";
}

function qualityFlagList(source) {
  const observation = source?.sample || source;
  return String(observation?.quality_flag || "")
    .split(";")
    .map((flag) => flag.trim())
    .filter(Boolean);
}

function hasUnitConversion(source) {
  if (source?.converted) return true;
  return qualityFlagList(source).some((flag) => flag.startsWith("unit_converted:"));
}

function conversionNotes(source) {
  const observation = source?.sample || source;
  const flag = qualityFlagList(observation).find((item) => item.startsWith("unit_converted:"));
  if (!flag) return [];
  const [, units = ""] = flag.split(":");
  const [from, to] = units.split("->");
  const raw = [observation?.raw_value, formatUnit(observation?.unit_raw || from)].filter(Boolean).join(" ");
  const converted = [formatUnit(from), formatUnit(to)].filter(Boolean).join(" to ");
  const prefix = raw ? `Converted from source value ${raw}` : "Converted from source units";
  return [`${prefix} (${converted}) for metric comparison.`];
}

function qualityNotes(source) {
  const notes = conversionNotes(source);
  for (const flag of qualityFlagList(source)) {
    if (flag === "impact_area_normalized") {
      notes.push("Area-normalized Izod values use kJ/m2 and are not directly comparable to ASTM linear Izod J/m values.");
    } else if (flag === "source_label_mismatch:izod_label_iso179") {
      notes.push("Source label says Izod, but ISO 179 is a Charpy impact method; stored under the method-consistent Charpy field.");
    } else if (flag.startsWith("impact_method_inferred:")) {
      notes.push("Impact property family inferred from the captured test method/unit.");
    } else if (flag.startsWith("impact_method_unit_mismatch:")) {
      notes.push("Captured impact method and unit appear to describe different impact-test families.");
    } else if (flag === "unit_not_converted") {
      notes.push("Source unit was captured but could not be converted safely.");
    }
  }
  return notes;
}

function unitMarker(source) {
  const notes = conversionNotes(source);
  if (!notes.length) return "";
  return `<span class="unit-marker" data-tip="${escapeAttr(notes.join("\n"))}">*</span>`;
}

function renderMetricValue(value, unit, source) {
  const text = [fmt(value), formatUnit(unit)].filter(Boolean).join(" ");
  return `${escapeHtml(text)}${unitMarker(source)}`;
}

function metricValueText(value, unit, source) {
  const text = [fmt(value), formatUnit(unit)].filter(Boolean).join(" ");
  return hasUnitConversion(source) ? `${text}*` : text;
}

function initTheme() {
  const requested = new URLSearchParams(window.location.search).get("theme");
  const stored = localStorage.getItem("filament-atlas-theme");
  const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  const theme = ["light", "dark"].includes(requested) ? requested : stored || (prefersDark ? "dark" : "light");
  document.documentElement.dataset.theme = theme;
  els.themeToggle.checked = theme === "dark";
  els.themeToggle.addEventListener("change", () => {
    const next = els.themeToggle.checked ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("filament-atlas-theme", next);
  });
}

function initControls() {
  const summary = state.data.summary;
  els.summaryText.textContent = `${summary.parsed_material_count} parsed records, ${summary.observation_count} observations, ${summary.numeric_observation_count} normalized numeric values`;
  els.generatedDate.textContent = state.data.generated_at || "";
  if (els.generatedDateFooter) els.generatedDateFooter.textContent = state.data.generated_at || "";

  renderStats(summary);
  renderKpis(summary);
  renderBaseLegend(summary.groups?.base_material || {});

  fillSelect(els.supplierFilter, "All suppliers", unique(state.materials.map((m) => m.supplier)));
  fillSelect(els.baseFilter, "All base materials", unique(state.materials.map((m) => m.base_material)));
  fillSelect(els.familyFilter, "All families", unique(state.materials.map((m) => m.material_family)));
  fillSelect(els.familyBaseSelect, "", unique(state.materials.map((m) => m.base_material)));
  els.familyBaseSelect.value = [...els.familyBaseSelect.options].some((o) => o.value === "PLA") ? "PLA" : els.familyBaseSelect.value;

  refreshPropertyScopeControls({ reset: true });

  updateRadarGroupOptions();
  const radarOptions = [...els.radarA.options].map((o) => o.value);
  els.radarA.value = radarOptions.includes("PETG") ? "PETG" : radarOptions[0] || "";
  els.radarB.value = radarOptions.includes("PLA") ? "PLA" : radarOptions[1] || radarOptions[0] || "";

  for (const el of [els.searchInput, els.supplierFilter, els.baseFilter, els.familyFilter, els.propertyFilter, els.parsedOnly]) {
    el.addEventListener("input", applyFilters);
    el.addEventListener("change", applyFilters);
  }

  els.resetFilters.addEventListener("click", clearAllFilters);
  els.clearFilters?.addEventListener("click", clearAllFilters);

  function clearAllFilters() {
    els.searchInput.value = "";
    els.supplierFilter.value = "";
    els.baseFilter.value = "";
    els.familyFilter.value = "";
    els.propertyFilter.value = "";
    els.parsedOnly.checked = true;
    applyFilters();
  }

  els.materialsBody.addEventListener("click", (event) => {
    const pinButton = event.target.closest(".pin-button");
    if (pinButton) {
      event.stopPropagation();
      togglePin(pinButton.dataset.id);
      return;
    }
    const row = event.target.closest("tr[data-id]");
    if (row) selectMaterial(row.dataset.id);
  });

  document.querySelectorAll("[data-sort-key]").forEach((button) => {
    button.addEventListener("click", () => {
      setTableSort(button.dataset.sortKey);
    });
  });

  document.addEventListener("click", (event) => {
    const feedbackButton = event.target.closest("[data-feedback-box]");
    if (feedbackButton) {
      event.stopPropagation();
      openFeedback(feedbackButton.dataset.feedbackBox);
      return;
    }

    const unpinButton = event.target.closest("[data-unpin-id]");
    if (unpinButton) {
      event.stopPropagation();
      togglePin(unpinButton.dataset.unpinId);
      return;
    }

    const pinButton = event.target.closest("[data-pin-id]");
    if (pinButton) {
      togglePin(pinButton.dataset.pinId);
      return;
    }

    const pinCard = event.target.closest("[data-select-id]");
    if (pinCard) selectMaterial(pinCard.dataset.selectId);
  });

  for (const el of [els.spreadMode, els.mapX, els.mapY, els.mapColorBy]) {
    el.addEventListener("change", () => {
      if (el === els.mapX || el === els.mapY) resetMapZoomState();
      renderSpread();
      renderMap();
    });
  }

  els.resetMapZoom?.addEventListener("click", () => {
    resetMapZoomState();
    renderMap();
  });

  els.materialMap.addEventListener("wheel", (event) => {
    if (!state.data || !els.mapX.value || !els.mapY.value) return;
    event.preventDefault();
    zoomMaterialMap(event);
  }, { passive: false });
  els.materialMap.addEventListener("pointerdown", startMapPan);
  els.materialMap.addEventListener("pointermove", dragMapPan);
  els.materialMap.addEventListener("pointerup", stopMapPan);
  els.materialMap.addEventListener("pointerleave", stopMapPan);
  els.materialMap.addEventListener("lostpointercapture", stopMapPan);

  els.familyBaseSelect.addEventListener("change", renderFamilyExplorer);

  for (const el of [els.radarA, els.radarB, els.radarGroup]) {
    el.addEventListener("change", () => {
      if (el === els.radarGroup) updateRadarGroupOptions();
      renderRadar();
    });
  }

  els.radarAxes.addEventListener("change", (event) => {
    const input = event.target.closest("input[type='checkbox']");
    if (!input) return;
    const key = input.value;
    if (input.checked) {
      if (state.radarSelectedKeys.length >= 10) {
        input.checked = false;
        return;
      }
      state.radarSelectedKeys = [...state.radarSelectedKeys, key];
    } else {
      state.radarSelectedKeys = state.radarSelectedKeys.filter((item) => item !== key);
    }
    renderRadarAxisControls();
    renderRadar();
  });

  els.radarChart.addEventListener("wheel", (event) => {
    event.preventDefault();
    const delta = event.deltaY < 0 ? 0.12 : -0.12;
    state.radarZoom = clamp(state.radarZoom + delta, 0.72, 2.8);
    renderRadar();
  }, { passive: false });

  els.advancedToggle.addEventListener("change", () => {
    state.advanced = els.advancedToggle.checked;
    refreshPropertyScopeControls({ reset: true });
    renderAll();
  });

  document.querySelectorAll(".detail-tab").forEach((button) => {
    button.addEventListener("click", () => {
      state.detailView = button.dataset.detailView;
      renderDetailTabs();
    });
  });

  document.querySelectorAll("[data-jump]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-jump]").forEach((b) => b.classList.remove("is-active"));
      button.classList.add("is-active");
      document.getElementById(button.dataset.jump)?.scrollIntoView({ block: "start" });
    });
  });
}

function scrollToHash() {
  if (!window.location.hash) return;
  const target = document.querySelector(window.location.hash);
  target?.scrollIntoView({ block: "start" });
}

function renderStats(summary) {
  const stats = [
    ["Records", summary.material_count],
    ["Parsed", summary.parsed_material_count],
    ["Observations", summary.observation_count],
    ["Numeric", summary.numeric_observation_count],
  ];
  els.corpusStats.innerHTML = stats.map(([k, v]) => `<dt>${k}</dt><dd>${fmtInt(v)}</dd>`).join("");
}

function renderKpis(summary) {
  const coverage = summary.coverage || [];
  const parsedPct = summary.material_count ? (summary.parsed_material_count / summary.material_count) * 100 : 0;
  const common = coverage
    .filter((c) => c.materials > 0)
    .sort((a, b) => b.materials - a.materials)
    .slice(0, 1)[0];
  const bases = Object.keys(summary.groups?.base_material || {}).length;
  const suppliers = unique(state.materials.map((m) => m.supplier)).length;
  const cards = [
    ["Parsed coverage", `${fmt(parsedPct)}%`, `${summary.parsed_material_count} of ${summary.material_count} records have extracted observations.`],
    ["Base materials", bases, "Every base gets a distinct color token, with generated hues for new entries."],
    ["Suppliers", suppliers, "Vendor records remain searchable and link back to source documents where possible."],
    ["Best-covered field", common?.label || "No data", `${common?.materials || 0} materials include this property.`],
  ];
  els.kpiCards.innerHTML = cards
    .map(([label, value, tip]) => `<div class="kpi-card" data-tip="${escapeAttr(tip)}"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>`)
    .join("");
}

function renderBaseLegend(groupCounts) {
  const entries = Object.entries(groupCounts).sort((a, b) => b[1] - a[1]);
  els.baseCount.textContent = `${entries.length} bases`;
  els.baseLegend.innerHTML = entries
    .map(([base, count]) => {
      const style = colorStyle(base, "base");
      return `<button class="legend-chip" type="button" style="${style}" data-tip="${escapeAttr(`${base}: ${count} records`)}" data-base="${escapeAttr(base)}">${escapeHtml(base)} ${count}</button>`;
    })
    .join("");
  els.baseLegend.querySelectorAll("[data-base]").forEach((chip) => {
    chip.addEventListener("click", () => {
      els.baseFilter.value = chip.dataset.base;
      applyFilters();
    });
  });
}

function applyFilters() {
  if (!state.data) return;
  const q = els.searchInput.value.trim().toLowerCase();
  const supplier = els.supplierFilter.value;
  const base = els.baseFilter.value;
  const family = els.familyFilter.value;
  const prop = els.propertyFilter.value;
  const parsedOnly = els.parsedOnly.checked;

  state.filtered = state.materials.filter((m) => {
    const text = `${m.product} ${m.supplier} ${m.base_material} ${m.material_family} ${(m.modifiers || []).join(" ")}`.toLowerCase();
    if (q && !text.includes(q)) return false;
    if (supplier && m.supplier !== supplier) return false;
    if (base && m.base_material !== base) return false;
    if (family && m.material_family !== family) return false;
    if (parsedOnly && !m.observations.length) return false;
    if (prop && !m.observations.some((o) => observationMatchesProperty(o, prop))) return false;
    return true;
  });

  if (!state.filtered.some((m) => m.material_id === state.selectedId)) {
    state.selectedId = state.filtered[0]?.material_id || null;
  }

  renderAll();
}

function renderAll() {
  renderMaterials();
  renderSelectedSummary();
  renderDetail();
  renderCompare();
  renderFamilyExplorer();
  renderSpread();
  renderMap();
  renderRadar();
  installFeedbackButtons();
  refreshIcons();
}

function renderMaterials() {
  const sorted = sortedMaterials(state.filtered);
  els.resultCount.textContent = `${state.filtered.length} shown`;
  updateSortHeaders();
  els.materialsBody.innerHTML = sorted
    .slice(0, 600)
    .map((m) => {
      const selected = m.material_id === state.selectedId ? " selected" : "";
      const valueCount = m.observations.filter((o) => o.value_nominal !== null).length;
      const baseStyle = colorStyle(m.base_material, "base");
      const pinActive = state.pinned.includes(m.material_id) ? " is-active" : "";
      return `<tr class="${selected}" data-id="${escapeAttr(m.material_id)}" data-tip="${escapeAttr(materialTip(m))}">
        <td>
          <div class="product-cell">
            <span class="material-dot" style="${baseStyle}"></span>
            <div><strong>${escapeHtml(m.product)}</strong><br><small>${escapeHtml((m.modifiers || []).join(", ") || m.material_family)}</small></div>
          </div>
        </td>
        <td>${escapeHtml(m.supplier)}</td>
        <td><span class="material-pill" style="${baseStyle}" data-tip="${escapeAttr(`${m.base_material} base material`)}">${escapeHtml(m.base_material)}</span></td>
        <td>${renderMiniFingerprint(m)}</td>
        <td>${valueCount}</td>
        <td><span class="status ${escapeAttr(m.status)}">${escapeHtml(statusLabel(m.status))}</span></td>
        <td><button class="pin-button${pinActive}" type="button" data-id="${escapeAttr(m.material_id)}" data-tip="${escapeAttr(pinActive ? "Remove from pinned compare" : "Pin for compare")}"><i data-lucide="pin"></i></button></td>
      </tr>`;
    })
    .join("");
}

function setTableSort(key) {
  if (!key) return;
  if (state.tableSort.key === key) {
    state.tableSort.direction = state.tableSort.direction === "asc" ? "desc" : "asc";
  } else {
    state.tableSort = { key, direction: "asc" };
  }
  renderMaterials();
  refreshIcons();
}

function sortedMaterials(materials) {
  const { key, direction } = state.tableSort;
  if (!key) return [...materials];
  const sign = direction === "desc" ? -1 : 1;
  return [...materials].sort((a, b) => compareTableValues(tableSortValue(a, key), tableSortValue(b, key)) * sign);
}

function tableSortValue(m, key) {
  if (key === "product") return m.product || "";
  if (key === "supplier") return m.supplier || "";
  if (key === "base") return m.base_material || "";
  if (key === "values") return m.observations.filter((o) => o.value_nominal !== null).length;
  if (key === "status") return statusLabel(m.status);
  if (key === "pin") return state.pinned.includes(m.material_id) ? 1 : 0;
  return "";
}

function compareTableValues(a, b) {
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}

function updateSortHeaders() {
  document.querySelectorAll("[data-sort-key]").forEach((button) => {
    const active = button.dataset.sortKey === state.tableSort.key;
    const direction = active ? state.tableSort.direction : "none";
    const indicator = button.querySelector(".sort-indicator");
    const th = button.closest("th");
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-label", `${button.dataset.sortLabel || button.textContent.trim()} sort ${active ? direction : "not active"}`);
    th?.setAttribute("aria-sort", active ? (direction === "asc" ? "ascending" : "descending") : "none");
    if (indicator) indicator.textContent = active ? (direction === "asc" ? "↑" : "↓") : "↕";
  });
}

function renderMiniFingerprint(m) {
  const scores = fingerprintScores(m).slice(0, 3);
  return `<div class="finger-mini">${scores
    .map((item) => {
      const style = colorStyle(m.base_material, "base");
      return `<div class="mini-track" style="${style}" data-tip="${escapeAttr(`${item.label}: ${fmt(item.score * 100)}% normalized`)}"><span style="width:${pct(item.score)}%"></span></div>`;
    })
    .join("")}</div>`;
}

function renderPinBars(m) {
  const style = colorStyle(m.base_material, "base");
  return `<div class="pin-bars">${fingerprintScores(m).slice(0, 4)
    .map((item) => `<span data-tip="${escapeAttr(`${item.label}: ${fmt(item.score * 100)}% normalized`)}"><i style="${style};width:${pct(item.score)}%"></i></span>`)
    .join("")}</div>`;
}

function selectFirstParsed() {
  state.selectedId = state.filtered.find((m) => m.observations.length)?.material_id || state.filtered[0]?.material_id || null;
  renderAll();
}

function selectMaterial(id) {
  if (!id || state.selectedId === id) return;
  state.selectedId = id;
  renderAll();
}

function renderSelectedSummary() {
  const m = selectedMaterial();
  if (!m) {
    els.selectedSummary.innerHTML = `<p>No material selected.</p>`;
    return;
  }
  const style = colorStyle(m.base_material, "base");
  els.selectedSummary.innerHTML = `<div class="selected-summary-header">
    <div>
      <span class="material-pill" style="${style}" data-tip="${escapeAttr(`${m.base_material} color token`)}">${escapeHtml(m.base_material)}</span>
      <h2>${escapeHtml(m.product)}</h2>
      <p>${escapeHtml(m.supplier)} / ${escapeHtml(m.material_family)} / ${m.observations.length} observations</p>
    </div>
    <button class="pin-button ${state.pinned.includes(m.material_id) ? "is-active" : ""}" type="button" data-pin-id="${escapeAttr(m.material_id)}" data-tip="Pin or unpin selected material"><i data-lucide="pin"></i></button>
  </div>
  <div class="fingerprint-card">${renderFingerprintRows(m)}</div>`;
}

function renderDetail() {
  const m = selectedMaterial();
  if (!m) {
    els.detailHero.innerHTML = `<h2 class="detail-title">Select a material</h2><p>Choose a row to inspect properties and sources.</p>`;
    els.propertyChips.innerHTML = "";
    els.heroMetrics.innerHTML = "";
    els.fingerprintPanel.innerHTML = "";
    els.thermalPanel.innerHTML = "";
    els.detailProperties.innerHTML = "";
    els.sourcePanel.innerHTML = "";
    return;
  }

  const baseStyle = colorStyle(m.base_material, "base");
  const familyStyle = colorStyle(m.material_family, "family", m.base_material);
  els.detailHero.style = baseStyle;
  els.detailHero.innerHTML = `<div class="detail-hero-main">
    <div>
      <span class="material-pill" style="${baseStyle}" data-tip="${escapeAttr(`${m.base_material}: base material color`)}">${escapeHtml(m.base_material)}</span>
      <h2 class="detail-title">${escapeHtml(m.product)}</h2>
      <p class="detail-meta">${escapeHtml(m.supplier)} / ${escapeHtml(m.material_family)} / ${escapeHtml(m.source_type)} / ${m.pages || "?"} page${m.pages === 1 ? "" : "s"}</p>
    </div>
    <div class="detail-actions">
      <button class="pin-button ${state.pinned.includes(m.material_id) ? "is-active" : ""}" type="button" data-pin-id="${escapeAttr(m.material_id)}" data-tip="Pin or unpin this material for compare"><i data-lucide="pin"></i></button>
    </div>
  </div>
  <div class="source-links">${renderSourceLinks(m, "compact")}</div>`;

  const chipValues = [
    { label: m.material_family, style: familyStyle, tip: "Material family" },
    ...(m.modifiers || []).map((modifier) => ({ label: modifier, style: colorStyle(`${m.base_material}-${modifier}`, "family", m.base_material), tip: "Modifier or product tag" })),
    { label: statusLabel(m.status), style: baseStyle, tip: m.quality_notes || "Parsing status" },
  ].filter((item) => item.label);
  els.propertyChips.innerHTML = chipValues
    .map((item) => `<span class="chip" style="${item.style}" data-tip="${escapeAttr(item.tip)}">${escapeHtml(item.label)}</span>`)
    .join("");

  renderHeroMetrics(m);
  els.fingerprintPanel.innerHTML = `<div class="fingerprint-card"><h3>Property Fingerprint</h3>${renderFingerprintRows(m)}</div>`;
  renderThermalPanel(m);
  renderProperties(m);
  renderSources(m);
  renderDetailTabs();
}

function renderHeroMetrics(m) {
  els.heroMetrics.innerHTML = heroMetricKeys
    .map((key) => {
      const stat = materialStat(m, key);
      const def = propDef(key);
      const score = stat?.value != null ? normalizedValue(key, stat.value) : 0;
      const value = stat ? renderMetricValue(stat.value, stat.unit || def?.canonical_unit || "", stat) : "No data";
      const tip = stat ? metricTip(m, key, stat) : `${def?.label || key}: no extracted value in this record.`;
      return `<div class="metric-card" style="${colorStyle(m.base_material, "base")}" data-tip="${escapeAttr(tip)}">
        <small>${escapeHtml(shortMetric(def?.label || key))}</small>
        <strong>${value}</strong>
        <div class="meter"><span style="width:${pct(score)}%"></span></div>
      </div>`;
    })
    .join("");
}

function renderFingerprintRows(m) {
  const style = colorStyle(m.base_material, "base");
  return fingerprintScores(m)
    .map((item) => `<div class="fingerprint-row" data-tip="${escapeAttr(item.tip)}">
      <span>${escapeHtml(item.label)}</span>
      <div class="fingerprint-track" style="${style}"><span style="width:${pct(item.score)}%"></span></div>
      <strong>${fmt(item.score * 100)}%</strong>
    </div>`)
    .join("");
}

function renderThermalPanel(m) {
  const rows = thermalKeys
    .map((key) => {
      const def = propDef(key);
      const stat = materialStat(m, key);
      const score = stat?.value != null ? normalizedValue(key, stat.value) : 0;
      const label = shortMetric(def?.label || key);
      const value = stat ? renderMetricValue(stat.value, def?.canonical_unit || stat.unit || "", stat) : "No data";
      const tip = stat ? metricTip(m, key, stat) : `${def?.label || key}: no extracted value.`;
      return `<div class="thermal-row" data-tip="${escapeAttr(tip)}">
        <span>${escapeHtml(label)}</span>
        <div class="thermal-track" style="${colorStyle(m.base_material, "base")}"><span style="width:${pct(score)}%"></span></div>
        <strong>${value}</strong>
      </div>`;
    })
    .join("");
  els.thermalPanel.innerHTML = `<div class="thermal-card"><h3>Thermal Envelope</h3>${rows}</div>`;
}

function renderProperties(m) {
  const observations = uniqueObservations(m.observations).filter(observationInPropertyScope);
  const grouped = groupBy(observations, (o) => o.category || propDef(o.property_key)?.category || "Other");
  const categories = Object.keys(grouped).sort(categorySort);
  els.detailProperties.classList.toggle("show-advanced", state.advanced);
  els.detailProperties.innerHTML = categories
    .map((category) => `<section class="prop-group">
      <h3>${escapeHtml(category)}</h3>
      ${grouped[category].map((o) => renderPropertyRow(o)).join("")}
    </section>`)
    .join("") || `<p>${escapeHtml(state.advanced ? (m.quality_notes || "No extracted property values.") : "No basic property values are available for this material. Switch to Advanced to inspect every extracted property.")}</p>`;
}

function renderPropertyRow(o) {
  const def = propDef(o.property_key);
  const val = o.value_nominal !== null && o.value_nominal !== undefined ? fmt(o.value_nominal) : String(o.raw_value || "");
  const unit = o.unit_canonical || def?.canonical_unit || "";
  const displayUnit = formatUnit(unit);
  const valueHtml = `${escapeHtml([val, displayUnit].filter(Boolean).join(" "))}${unitMarker(o)}`;
  const orient = directionalPropertyKeys.has(o.property_key) ? orientationLabel(o.orientation) : "";
  const meta = [o.test_method, o.orientation, o.condition, o.quality_flag].filter(Boolean).join(" / ");
  const tip = [
    def?.label || o.property_label || o.property_key,
    metricValueText(val, unit, o),
    meta,
    ...qualityNotes(o),
    o.source_context,
  ].filter(Boolean).join("\n");
  return `<div class="prop-row" data-tip="${escapeAttr(tip)}">
    <div>
      <strong>${escapeHtml(def?.label || o.property_label || o.property_key)}${orient ? ` <span class="orientation-badge ${escapeAttr(orient.toLowerCase())}">${escapeHtml(orient)}</span>` : ""}</strong><br>
      <small>${escapeHtml(meta || o.raw_label || "Typical value")}</small>
    </div>
    <div class="prop-value">${valueHtml}</div>
    <div class="prop-context">${escapeHtml(o.source_context || "No source context captured.")}</div>
  </div>`;
}

function renderSources(m) {
  const info = sourceInfo(m);
  const methods = unique(m.observations.map((o) => o.test_method)).slice(0, 12);
  const contexts = unique(m.observations.map((o) => o.source_context).filter(Boolean)).slice(0, 4);
  els.sourcePanel.innerHTML = `<div class="source-card">
    <div class="source-card-header">
      <span class="source-dot" style="${colorStyle(m.base_material, "base")}"></span>
      <strong>${escapeHtml(info.document_title || m.product)}</strong>
    </div>
    <small>${escapeHtml(normalizePath(m.source_file || "No local source path"))}</small>
    <div class="source-links">${renderSourceLinks(m, "full")}</div>
    <p>${escapeHtml([m.source_type, m.pages ? `${m.pages} page${m.pages === 1 ? "" : "s"}` : "", info.retrieved_at ? `retrieved ${info.retrieved_at}` : ""].filter(Boolean).join(" / "))}</p>
  </div>
  <div class="source-card">
    <strong>Extraction Notes</strong>
    <p>${escapeHtml(m.quality_notes || "No quality notes recorded for this material.")}</p>
    <p>${escapeHtml(methods.length ? `Test methods found: ${methods.join(", ")}` : "No test methods captured in extracted observations.")}</p>
  </div>
  <div class="source-card">
    <strong>Source Context Samples</strong>
    ${contexts.length ? contexts.map((c) => `<small>${escapeHtml(c)}</small>`).join("") : "<p>No source-context snippets captured.</p>"}
  </div>`;
}

function renderDetailTabs() {
  document.querySelectorAll(".detail-tab").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.detailView === state.detailView);
  });
  els.detailProperties.hidden = state.detailView !== "properties";
  els.sourcePanel.hidden = state.detailView !== "sources";
}

function renderSourceLinks(m, mode) {
  const info = sourceInfo(m);
  const links = [];
  if (info.source_page_url) links.push(`<a href="${escapeAttr(info.source_page_url)}" target="_blank" rel="noreferrer">Source page</a>`);
  if (info.download_url) links.push(`<a href="${escapeAttr(info.download_url)}" target="_blank" rel="noreferrer">Vendor PDF</a>`);
  if (m.source_file && shouldShowLocalSourceLinks()) {
    links.push(`<a href="${escapeAttr(localSourceHref(m.source_file))}" target="_blank" rel="noreferrer">Local datasheet</a>`);
  }
  if (!links.length) return `<span class="status">No links captured</span>`;
  return mode === "compact" ? links.slice(0, 3).join("") : links.join("");
}

function renderCompare() {
  els.pinCount.textContent = `${state.pinned.length}/5 pinned`;
  const pinnedMaterials = state.pinned.map((id) => materialById(id)).filter(Boolean);
  const emptySlots = Math.max(0, 5 - pinnedMaterials.length);
  els.pinTray.innerHTML = [
    ...pinnedMaterials.map((m) => {
      const active = m.material_id === state.selectedId ? " is-active" : "";
      return `<div class="pin-card${active}" style="${colorStyle(m.base_material, "base")}" data-select-id="${escapeAttr(m.material_id)}" data-tip="${escapeAttr(materialTip(m))}">
        <button class="pin-remove" type="button" data-unpin-id="${escapeAttr(m.material_id)}" data-tip="Remove from pinned compare"><i data-lucide="x"></i></button>
        <small>${escapeHtml(m.supplier)}</small>
        <strong>${escapeHtml(m.product)}</strong>
        ${renderPinBars(m)}
        <span>${escapeHtml(m.base_material)} / ${m.observations.length} obs.</span>
      </div>`;
    }),
    ...Array.from({ length: emptySlots }, (_, i) => `<div class="pin-card pin-card-empty" data-tip="Pin a material from the table to fill this compare slot."><small>Slot ${pinnedMaterials.length + i + 1}</small><strong>Pin material</strong></div>`),
  ].join("");

  if (!pinnedMaterials.length) {
    els.compareMatrix.innerHTML = `<p style="padding: 14px 15px;">Pin materials to build a comparison matrix.</p>`;
    return;
  }

  const rows = state.advanced
    ? numericPropertyOptions().map(([key]) => key)
    : propertyScopeKeys();

  els.compareMatrix.innerHTML = `<table class="compare-table">
    <thead><tr><th>Property</th>${pinnedMaterials.map((m) => `<th>${escapeHtml(m.product)}</th>`).join("")}</tr></thead>
    <tbody>${rows
      .map((key) => {
        const def = displayProp(key);
        return `<tr>
          <td><strong>${escapeHtml(def?.label || key)}</strong><br><small>${escapeHtml(formatUnit(def?.canonical_unit || ""))}</small></td>
          ${pinnedMaterials
            .map((m) => {
              const stat = materialStat(m, key);
              const value = stat ? renderMetricValue(stat.value, stat.unit || def?.canonical_unit || "", stat) : "No data";
              return `<td data-tip="${escapeAttr(stat ? metricTip(m, key, stat) : `${m.product}: no ${def?.label || key}`)}">${value}</td>`;
            })
            .join("")}
        </tr>`;
      })
      .join("")}</tbody>
  </table>`;
}

function togglePin(id) {
  if (!id) return;
  if (state.pinned.includes(id)) {
    state.pinned = state.pinned.filter((x) => x !== id);
  } else if (state.pinned.length < 5) {
    state.pinned = [...state.pinned, id];
  }
  renderMaterials();
  renderSelectedSummary();
  renderDetail();
  renderCompare();
  renderRadar();
  refreshIcons();
}

function renderFamilyExplorer() {
  if (!els.familyStats || !state.data) return;
  const base = els.familyBaseSelect.value || "PLA";
  const materials = state.materials.filter((m) => m.base_material === base && m.observations.length);
  const parsedCount = materials.length;
  els.familySummary.textContent = `${parsedCount} parsed ${base} records; whiskers show min/max, boxes show Q1-Q3, the tick is median, and the dot is mean.`;
  const rows = numericPropertyOptions()
    .map(([key]) => ({ key, def: displayProp(key), stat: statForMaterials(materials, key) }))
    .filter(({ stat }) => stat && stat.count)
    .sort((a, b) => categorySort(a.def.category || "", b.def.category || "") || a.def.label.localeCompare(b.def.label));

  els.familyStats.innerHTML = `<table class="family-table">
    <thead><tr><th>Property</th><th>Count</th><th>Distribution</th><th>Median / Mean</th><th>Max record</th></tr></thead>
    <tbody>${rows.map(({ key, def, stat }) => {
      const unit = formatUnit(def.canonical_unit || stat.unit || "");
      const tip = `${def.label}\nmin ${fmt(stat.min)}, Q1 ${fmt(stat.q1)}, median ${fmt(stat.median)}, mean ${fmt(stat.avg)}, Q3 ${fmt(stat.q3)}, max ${fmt(stat.max)} ${unit}\nMax: ${stat.maxMaterial.product}`;
      return `<tr data-tip="${escapeAttr(tip)}">
        <td><strong>${escapeHtml(def.label)}</strong><br><small>${escapeHtml(def.category || "")} / ${escapeHtml(unit)}</small></td>
        <td>${fmtInt(stat.count)}</td>
        <td>${renderBoxPlot(stat, base)}<small>${fmt(stat.min)} - ${fmt(stat.max)} ${escapeHtml(unit)}</small></td>
        <td><strong>${fmt(stat.median)} / ${fmt(stat.avg)} ${escapeHtml(unit)}</strong></td>
        <td>${escapeHtml(stat.maxMaterial.product)}<br><small>${escapeHtml(stat.maxMaterial.supplier)} / ${fmt(stat.max)} ${escapeHtml(unit)}</small></td>
      </tr>`;
    }).join("")}</tbody>
  </table>`;
}

function renderBoxPlot(stat, base) {
  const span = stat.max - stat.min || 1;
  const pos = (value) => clamp(((value - stat.min) / span) * 100, 0, 100);
  const q1 = pos(stat.q1);
  const q3 = pos(stat.q3);
  const median = pos(stat.median);
  const mean = pos(stat.avg);
  return `<div class="boxplot" style="${colorStyle(base, "base")}">
    <span class="boxplot-whisker"></span>
    <span class="boxplot-box" style="left:${fmt(q1)}%;width:${fmt(Math.max(1, q3 - q1))}%"></span>
    <span class="boxplot-median" style="left:${fmt(median)}%"></span>
    <span class="boxplot-mean" style="left:${fmt(mean)}%"></span>
  </div>`;
}

function renderSpread() {
  const m = selectedMaterial();
  if (!m) {
    els.spreadHint.textContent = "Select a material to see comparable entries.";
    els.spreadRows.innerHTML = "";
    return;
  }
  const mode = els.spreadMode.value;
  const groupValue = m[mode] || "Unknown";
  const peers = state.materials.filter((x) => x[mode] === groupValue && x.observations.length);
  els.spreadHint.textContent = `${peers.length} parsed records in ${mode === "base_material" ? "base material" : "family"}: ${groupValue}`;
  const stats = summarizeGroup(peers);
  const rows = propertyScopeKeys()
    .map((key) => ({ key, def: displayProp(key), stat: statForMaterials(peers, key) }))
    .filter((x) => x.stat && x.stat.count > 0)
    .slice(0, 12);

  els.spreadRows.innerHTML = rows
    .map(({ key, def, stat }) => {
      const score = normalizedValue(key, stat.avg);
      const tip = `${def?.label || key}\nmin ${fmt(stat.min)}, avg ${fmt(stat.avg)}, max ${fmt(stat.max)} ${formatUnit(def?.canonical_unit || "")}\n${stat.count} numeric observations in this peer group.`;
      return `<div class="spread-line" data-tip="${escapeAttr(tip)}">
        <div class="spread-meta"><strong>${escapeHtml(def?.label || key)}</strong><span>${fmt(stat.min)} / ${fmt(stat.avg)} / ${fmt(stat.max)} ${escapeHtml(formatUnit(def?.canonical_unit || ""))}</span></div>
        <div class="bar" style="${colorStyle(groupValue, mode === "base_material" ? "base" : "family", m.base_material)}"><span style="width:${pct(score)}%"></span></div>
      </div>`;
    })
    .join("") || "<p>No comparable numeric properties found.</p>";
}

function renderMap() {
  if (!state.data) return;
  const xKey = els.mapX.value;
  const yKey = els.mapY.value;
  const xDef = displayProp(xKey);
  const yDef = displayProp(yKey);
  const xFullRange = dbMinMax(xKey);
  const yFullRange = dbMinMax(yKey);
  ensureMapZoomState(xKey, yKey, xFullRange, yFullRange);
  const ranges = visibleMapRanges(xFullRange, yFullRange);
  const allPoints = state.filtered
    .map((m) => {
      const xStat = materialStat(m, xKey);
      const yStat = materialStat(m, yKey);
      const x = xStat?.value;
      const y = yStat?.value;
      if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
      return { m, x, y, xStat, yStat };
    })
    .filter(Boolean)
    .slice(0, 320);
  const points = allPoints.filter(({ x, y }) => x >= ranges.x.min && x <= ranges.x.max && y >= ranges.y.min && y <= ranges.y.max);

  if (!allPoints.length) {
    els.materialMap.innerHTML = `<p>No materials in this filter set have both selected plot properties.</p>`;
    return;
  }

  const w = 880;
  const h = 520;
  const pad = { l: 72, r: 30, t: 28, b: 70 };
  const plotW = w - pad.l - pad.r;
  const plotH = h - pad.t - pad.b;
  const sx = (v) => pad.l + ((v - ranges.x.min) / (ranges.x.max - ranges.x.min || 1)) * plotW;
  const sy = (v) => pad.t + (1 - (v - ranges.y.min) / (ranges.y.max - ranges.y.min || 1)) * plotH;
  const xTicks = linearTicks(ranges.x.min, ranges.x.max, plotW, 86);
  const yTicks = linearTicks(ranges.y.min, ranges.y.max, plotH, 74);
  const grid = [
    ...xTicks.map((value) => {
      const x = sx(value);
      return `<line class="map-grid-line" x1="${x}" y1="${pad.t}" x2="${x}" y2="${pad.t + plotH}"/>
        <text class="axis-tick" x="${x}" y="${pad.t + plotH + 22}" text-anchor="middle">${escapeHtml(formatAxisValue(value))}</text>`;
    }),
    ...yTicks.map((value) => {
      const y = sy(value);
      return `<line class="map-grid-line" x1="${pad.l}" y1="${y}" x2="${pad.l + plotW}" y2="${y}"/>
        <text class="axis-tick" x="${pad.l - 10}" y="${y + 4}" text-anchor="end">${escapeHtml(formatAxisValue(value))}</text>`;
    }),
  ].join("");
  const colorBy = els.mapColorBy.value;
  const circles = points
    .map(({ m, x, y, xStat, yStat }) => {
      const tensile = materialStat(m, "tensile_strength")?.value;
      const r = 5 + normalizedValue("tensile_strength", tensile || 0) * 10;
      const colorValue = m[colorBy] || "Unknown";
      const style = colorStyle(colorValue, colorBy === "base_material" ? "base" : "family", m.base_material);
      const active = m.material_id === state.selectedId ? " is-active" : "";
      const tip = `${m.product}\n${m.supplier} / ${m.base_material}\n${xDef?.label || xKey}: ${metricValueText(x, xDef?.canonical_unit || xStat?.unit || "", xStat)}\n${yDef?.label || yKey}: ${metricValueText(y, yDef?.canonical_unit || yStat?.unit || "", yStat)}`;
      return `<circle class="map-point${active}" data-id="${escapeAttr(m.material_id)}" data-tip="${escapeAttr(tip)}" cx="${sx(x)}" cy="${sy(y)}" r="${r}" fill="hsl(var(--mat-h) var(--mat-s) var(--mat-l))" fill-opacity="0.78" stroke="var(--surface)" stroke-width="1" style="${style}"></circle>`;
    })
    .join("");
  const selectedPoint = points.find(({ m }) => m.material_id === state.selectedId);
  const selectedLabel = selectedPoint
    ? `<text class="point-label" x="${sx(selectedPoint.x) + 13}" y="${sy(selectedPoint.y) - 10}">${escapeHtml(shortProduct(selectedPoint.m.product))}</text>`
    : "";

  els.mapZoomLabel.textContent = `Zoom ${Math.round(state.mapZoom * 100)}%`;
  const pointSummary = state.mapZoom > 1 ? `${points.length}/${allPoints.length} visible` : `${allPoints.length} plotted`;
  els.materialMap.innerHTML = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Material map" data-plot-left="${pad.l}" data-plot-top="${pad.t}" data-plot-width="${plotW}" data-plot-height="${plotH}">
    <defs><clipPath id="mapPlotClip"><rect x="${pad.l}" y="${pad.t}" width="${plotW}" height="${plotH}"/></clipPath></defs>
    <rect x="${pad.l}" y="${pad.t}" width="${plotW}" height="${plotH}" fill="var(--surface-2)" stroke="var(--line)"/>
    ${grid}
    <line x1="${pad.l}" y1="${pad.t + plotH}" x2="${pad.l + plotW}" y2="${pad.t + plotH}" stroke="var(--line-strong)" stroke-width="1.2"/>
    <line x1="${pad.l}" y1="${pad.t}" x2="${pad.l}" y2="${pad.t + plotH}" stroke="var(--line-strong)" stroke-width="1.2"/>
    <g clip-path="url(#mapPlotClip)">${circles}</g>
    ${selectedLabel}
    <text class="axis-text" x="${pad.l + plotW / 2}" y="${h - 20}" text-anchor="middle">${escapeHtml(xDef?.label || xKey)} (${escapeHtml(formatUnit(xDef?.canonical_unit || ""))})</text>
    <text class="axis-text" transform="translate(22 ${pad.t + plotH / 2}) rotate(-90)" text-anchor="middle">${escapeHtml(yDef?.label || yKey)} (${escapeHtml(formatUnit(yDef?.canonical_unit || ""))})</text>
    <text class="axis-text" x="${pad.l + plotW}" y="${pad.t - 10}" text-anchor="end">${escapeHtml(pointSummary)}</text>
  </svg>`;

  els.materialMap.querySelectorAll(".map-point").forEach((point) => {
    point.addEventListener("click", () => selectMaterial(point.dataset.id));
  });
}

function ensureMapZoomState(xKey, yKey, xRange, yRange) {
  if (state.mapKeys.x === xKey && state.mapKeys.y === yKey && state.mapCenter) return;
  state.mapKeys = { x: xKey, y: yKey };
  state.mapZoom = 1;
  state.mapCenter = {
    x: (xRange.min + xRange.max) / 2,
    y: (yRange.min + yRange.max) / 2,
  };
}

function resetMapZoomState() {
  state.mapZoom = 1;
  state.mapCenter = null;
  state.mapPan = null;
  els.materialMap.classList.remove("is-panning");
}

function visibleMapRanges(xRange, yRange) {
  const xSpan = (xRange.max - xRange.min || 1) / state.mapZoom;
  const ySpan = (yRange.max - yRange.min || 1) / state.mapZoom;
  const center = state.mapCenter || {
    x: (xRange.min + xRange.max) / 2,
    y: (yRange.min + yRange.max) / 2,
  };
  const xCenter = clamp(center.x, xRange.min + xSpan / 2, xRange.max - xSpan / 2);
  const yCenter = clamp(center.y, yRange.min + ySpan / 2, yRange.max - ySpan / 2);
  state.mapCenter = { x: xCenter, y: yCenter };
  return {
    x: { min: xCenter - xSpan / 2, max: xCenter + xSpan / 2 },
    y: { min: yCenter - ySpan / 2, max: yCenter + ySpan / 2 },
  };
}

function zoomMaterialMap(event) {
  const xKey = els.mapX.value;
  const yKey = els.mapY.value;
  const xFullRange = dbMinMax(xKey);
  const yFullRange = dbMinMax(yKey);
  ensureMapZoomState(xKey, yKey, xFullRange, yFullRange);
  const svg = els.materialMap.querySelector("svg");
  if (!svg) return;
  const rect = svg.getBoundingClientRect();
  const pad = { l: 72, r: 30, t: 28, b: 70 };
  const w = 880;
  const h = 520;
  const plotW = w - pad.l - pad.r;
  const plotH = h - pad.t - pad.b;
  const svgX = ((event.clientX - rect.left) / Math.max(1, rect.width)) * w;
  const svgY = ((event.clientY - rect.top) / Math.max(1, rect.height)) * h;
  const fx = clamp((svgX - pad.l) / plotW, 0, 1);
  const fy = clamp((svgY - pad.t) / plotH, 0, 1);
  const ranges = visibleMapRanges(xFullRange, yFullRange);
  const cursorX = ranges.x.min + fx * (ranges.x.max - ranges.x.min);
  const cursorY = ranges.y.max - fy * (ranges.y.max - ranges.y.min);
  const nextZoom = clamp(state.mapZoom * (event.deltaY < 0 ? 1.2 : 1 / 1.2), 1, 18);
  const xSpan = (xFullRange.max - xFullRange.min || 1) / nextZoom;
  const ySpan = (yFullRange.max - yFullRange.min || 1) / nextZoom;
  const xMin = cursorX - fx * xSpan;
  const yMin = cursorY - (1 - fy) * ySpan;
  state.mapZoom = nextZoom;
  state.mapCenter = {
    x: clamp(xMin + xSpan / 2, xFullRange.min + xSpan / 2, xFullRange.max - xSpan / 2),
    y: clamp(yMin + ySpan / 2, yFullRange.min + ySpan / 2, yFullRange.max - ySpan / 2),
  };
  renderMap();
}

function startMapPan(event) {
  if (!state.data || state.mapZoom <= 1 || event.button !== 0) return;
  if (event.target.closest?.(".map-point")) return;
  const svg = els.materialMap.querySelector("svg");
  if (!svg) return;
  const point = mapSvgPoint(event, svg);
  const bounds = mapPlotBounds(svg);
  if (!bounds || point.x < bounds.left || point.x > bounds.right || point.y < bounds.top || point.y > bounds.bottom) return;
  event.preventDefault();
  state.mapPan = { x: event.clientX, y: event.clientY };
  els.materialMap.classList.add("is-panning");
  els.materialMap.setPointerCapture?.(event.pointerId);
}

function dragMapPan(event) {
  if (!state.mapPan || state.mapZoom <= 1) return;
  const dx = event.clientX - state.mapPan.x;
  const dy = event.clientY - state.mapPan.y;
  if (!dx && !dy) return;
  event.preventDefault();

  const xFullRange = dbMinMax(els.mapX.value);
  const yFullRange = dbMinMax(els.mapY.value);
  const ranges = visibleMapRanges(xFullRange, yFullRange);
  const svg = els.materialMap.querySelector("svg");
  const bounds = mapPlotBounds(svg);
  if (!bounds) return;
  const rect = svg.getBoundingClientRect();
  const pxPerSvgX = rect.width / 880;
  const pxPerSvgY = rect.height / 520;
  const plotPxW = Math.max(1, bounds.width * pxPerSvgX);
  const plotPxH = Math.max(1, bounds.height * pxPerSvgY);
  const xSpan = ranges.x.max - ranges.x.min || 1;
  const ySpan = ranges.y.max - ranges.y.min || 1;

  state.mapCenter = {
    x: state.mapCenter.x - (dx / plotPxW) * xSpan,
    y: state.mapCenter.y + (dy / plotPxH) * ySpan,
  };
  state.mapPan = { x: event.clientX, y: event.clientY };
  visibleMapRanges(xFullRange, yFullRange);
  renderMap();
}

function stopMapPan(event) {
  if (!state.mapPan) return;
  state.mapPan = null;
  els.materialMap.classList.remove("is-panning");
  if (event?.pointerId !== undefined) {
    try {
      els.materialMap.releasePointerCapture?.(event.pointerId);
    } catch (_) {
      // Pointer capture may already be released by the browser.
    }
  }
}

function mapSvgPoint(event, svg) {
  const rect = svg.getBoundingClientRect();
  return {
    x: ((event.clientX - rect.left) / Math.max(1, rect.width)) * 880,
    y: ((event.clientY - rect.top) / Math.max(1, rect.height)) * 520,
  };
}

function mapPlotBounds(svg) {
  if (!svg) return null;
  const left = Number(svg.dataset.plotLeft || 72);
  const top = Number(svg.dataset.plotTop || 28);
  const width = Number(svg.dataset.plotWidth || 778);
  const height = Number(svg.dataset.plotHeight || 422);
  return { left, top, width, height, right: left + width, bottom: top + height };
}

function linearTicks(min, max, pixels, targetPixels) {
  const count = Math.max(3, Math.min(12, Math.round(pixels / targetPixels) + 1));
  if (!Number.isFinite(min) || !Number.isFinite(max) || max <= min) return [];
  return Array.from({ length: count }, (_, i) => min + ((max - min) * i) / (count - 1));
}

function formatAxisValue(value) {
  const abs = Math.abs(value);
  if (abs >= 1000) return value.toFixed(0);
  if (abs >= 100) return value.toFixed(1).replace(/\.0$/, "");
  if (abs >= 10) return value.toFixed(2).replace(/\.?0+$/, "");
  if (abs >= 1) return value.toFixed(2).replace(/\.?0+$/, "");
  return value.toFixed(3).replace(/\.?0+$/, "");
}

function initFeedback() {
  if (!els.feedbackModal || !els.feedbackForm) return;
  els.feedbackClose?.addEventListener("click", closeFeedback);
  els.feedbackModal.addEventListener("click", (event) => {
    if (event.target === els.feedbackModal) closeFeedback();
  });
  els.feedbackForm.addEventListener("submit", (event) => {
    event.preventDefault();
    saveFeedbackReport();
  });
  els.feedbackExport?.addEventListener("click", exportFeedbackReports);
}

function installFeedbackButtons() {
  const boxes = document.querySelectorAll([
    ".stats-panel",
    ".legend-panel",
    ".table-panel",
    ".selected-summary",
    ".detail-panel",
    ".compare-panel",
    ".family-panel",
    ".map-panel",
    ".spread-panel",
    ".radar-panel",
    ".corpus-summary-panel",
    ".kpi-card",
    ".metric-card",
    ".pin-card",
  ].join(","));
  boxes.forEach((box) => {
    box.classList.add("feedback-host");
    if ([...box.children].some((child) => child.classList?.contains("feedback-button"))) return;
    const label = feedbackLabelForBox(box);
    const button = document.createElement("button");
    button.className = "feedback-button";
    button.type = "button";
    button.dataset.feedbackBox = label;
    button.dataset.tip = `Record a bug for ${label}`;
    button.innerHTML = `<i data-lucide="bug"></i><span class="sr-only">Record bug for ${escapeHtml(label)}</span>`;
    box.appendChild(button);
  });
}

function feedbackLabelForBox(box) {
  const heading = box.querySelector("h1,h2,h3,strong,small");
  const label = heading?.textContent?.trim();
  if (label) return label.replace(/\s+/g, " ").slice(0, 90);
  return box.className
    .split(/\s+/)
    .filter((name) => name && name !== "feedback-host")
    .join(" ")
    .replace(/-/g, " ") || "Interface box";
}

function openFeedback(boxLabel) {
  const selected = selectedMaterial();
  state.feedbackContext = {
    box: boxLabel || "Interface box",
    selected_material_id: selected?.material_id || null,
    selected_material: selected?.product || null,
    url: window.location.href,
    theme: document.documentElement.dataset.theme || "light",
    filters: {
      search: els.searchInput?.value || "",
      supplier: els.supplierFilter?.value || "",
      base: els.baseFilter?.value || "",
      family: els.familyFilter?.value || "",
      property: els.propertyFilter?.value || "",
      parsed_only: Boolean(els.parsedOnly?.checked),
    },
    map: {
      x: els.mapX?.value || "",
      y: els.mapY?.value || "",
      zoom: state.mapZoom,
    },
    timestamp: new Date().toISOString(),
  };
  els.feedbackContext.textContent = selected
    ? `${state.feedbackContext.box} / ${selected.product}`
    : state.feedbackContext.box;
  els.feedbackText.value = "";
  updateFeedbackSubmitButton();
  els.feedbackModal.hidden = false;
  window.setTimeout(() => els.feedbackText.focus(), 0);
}

function closeFeedback() {
  if (!els.feedbackModal) return;
  els.feedbackModal.hidden = true;
  state.feedbackContext = null;
}

function saveFeedbackReport() {
  const note = els.feedbackText.value.trim();
  if (!note) return;
  const reports = readFeedbackReports();
  const report = { ...state.feedbackContext, note };
  reports.push(report);
  localStorage.setItem("filament-atlas-feedback", JSON.stringify(reports, null, 2));
  const issueUrl = githubIssueUrl(report);
  closeFeedback();
  if (issueUrl) window.open(issueUrl, "_blank", "noopener,noreferrer");
}

function readFeedbackReports() {
  try {
    const parsed = JSON.parse(localStorage.getItem("filament-atlas-feedback") || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch (_) {
    return [];
  }
}

function exportFeedbackReports() {
  const reports = readFeedbackReports();
  const blob = new Blob([JSON.stringify(reports, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `filament-atlas-feedback-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function updateFeedbackSubmitButton() {
  if (!els.feedbackSubmit) return;
  const hasGithubTarget = Boolean(githubRepo());
  const icon = hasGithubTarget ? "external-link" : "save";
  const label = hasGithubTarget ? "Open Issue" : "Save Report";
  els.feedbackSubmit.innerHTML = `<i data-lucide="${icon}"></i><span>${label}</span>`;
  els.feedbackSubmit.dataset.tip = hasGithubTarget ? "Open a prefilled GitHub issue" : "Save this report in local browser storage";
  refreshIcons();
}

function githubIssueUrl(report) {
  const repo = githubRepo();
  if (!repo) return "";
  const title = `${appConfig.issueTitlePrefix || "[Atlas feedback]"} ${report.selected_material || report.box || "Site feedback"}`;
  const body = feedbackIssueBody(report);
  const params = new URLSearchParams({ title, body });
  const labels = Array.isArray(appConfig.githubLabels) ? appConfig.githubLabels.filter(Boolean) : [];
  if (labels.length) params.set("labels", labels.join(","));
  return `https://github.com/${repo}/issues/new?${params.toString()}`;
}

function feedbackIssueBody(report) {
  const context = {
    box: report.box,
    selected_material_id: report.selected_material_id,
    selected_material: report.selected_material,
    page: report.url,
    theme: report.theme,
    filters: report.filters,
    map: report.map,
    timestamp: report.timestamp,
  };
  return [
    "### Feedback",
    clampText(report.note, 2400),
    "",
    "### Captured context",
    "```json",
    JSON.stringify(context, null, 2),
    "```",
  ].join("\n");
}

function githubRepo() {
  const configured = String(appConfig.githubRepo || "").trim();
  if (/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(configured)) return configured;
  const match = window.location.hostname.match(/^([A-Za-z0-9-]+)\.github\.io$/);
  const repo = window.location.pathname.split("/").filter(Boolean)[0];
  return match && repo ? `${match[1]}/${repo}` : "";
}

function clampText(text, maxLength) {
  const value = String(text || "");
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value;
}

function updateRadarGroupOptions() {
  const field = els.radarGroup.value;
  const groups = unique(state.materials.filter((m) => m.observations.length).map((m) => m[field]));
  fillSelect(els.radarA, "", groups);
  fillSelect(els.radarB, "", groups);
}

function renderRadarAxisControls() {
  const selected = new Set(state.radarSelectedKeys);
  els.radarAxes.innerHTML = numericPropertyOptions()
    .filter(([key]) => radarAxes.includes(splitPropertyKey(key).baseKey) || selected.has(key))
    .map(([key]) => {
      const def = displayProp(key);
      const checked = selected.has(key) ? " checked" : "";
      const disabled = !checked && selected.size >= 10 ? " disabled" : "";
      return `<label class="radar-axis-option" data-tip="${escapeAttr(def.label)}">
        <input type="checkbox" value="${escapeAttr(key)}"${checked}${disabled}>
        <span>${escapeHtml(shortMetric(def.label))}</span>
      </label>`;
    })
    .join("");
}

function renderRadar() {
  if (!state.data) return;
  const field = els.radarGroup.value;
  const a = els.radarA.value;
  const b = els.radarB.value;
  const matsA = state.materials.filter((m) => m[field] === a && m.observations.length);
  const matsB = state.materials.filter((m) => m[field] === b && m.observations.length);
  const pinnedMaterials = state.pinned.map((id) => materialById(id)).filter(Boolean).slice(0, 4);
  const axes = state.radarSelectedKeys
    .map((key) => ({ key, def: displayProp(key), db: dbMinMax(key), max: statForMaterials(state.materials, key) }))
    .filter((x) => {
      if (!x.def || x.db.max <= x.db.min) return false;
      if (pinnedMaterials.length) return pinnedMaterials.some((m) => materialStat(m, x.key));
      return statForMaterials(matsA, x.key) || statForMaterials(matsB, x.key);
    })
    .slice(0, 10);
  const series = pinnedMaterials.length
    ? pinnedMaterials.map((m) => radarMaterialSeries(m, axes))
    : [
        radarGroupSeries(a || "A", matsA, axes, "group-a"),
        radarGroupSeries(b || "B", matsB, axes, "group-b"),
      ];
  els.radarChart.innerHTML = drawRadar(axes, series);
  els.radarLegend.innerHTML = series
    .map((item) => `<span style="${item.style}" data-tip="${escapeAttr(item.tip)}">${escapeHtml(item.label)}${item.missing ? ` (${item.missing} missing)` : ""}</span>`)
    .join("");
  els.radarZoomLabel.textContent = `Zoom ${Math.round(state.radarZoom * 100)}%`;
}

function radarMaterialSeries(material, axes) {
  const stats = Object.fromEntries(axes.map((axis) => [axis.key, materialStat(material, axis.key)]));
  const missing = axes.filter((axis) => !stats[axis.key]).length;
  return {
    label: material.product,
    style: colorStyle(material.base_material, "base"),
    stats,
    missing,
    tip: `${material.product}\n${material.supplier} / ${material.base_material}\n${axes.length - missing} of ${axes.length} radar axes available.`,
  };
}

function radarGroupSeries(label, materials, axes, className) {
  const stats = Object.fromEntries(axes.map((axis) => [axis.key, statForMaterials(materials, axis.key)]));
  const missing = axes.filter((axis) => !stats[axis.key]).length;
  return {
    label,
    className,
    style: className === "group-a" ? "--mat-h:177;--mat-s:70%;" : "--mat-h:18;--mat-s:72%;",
    stats,
    missing,
    tip: `${label}\nGroup average series\n${axes.length - missing} of ${axes.length} radar axes available.`,
  };
}

function drawRadar(axes, series) {
  if (!axes.length) return "<p>No overlapping numeric axes available.</p>";
  const w = 600;
  const h = 360;
  const cx = w / 2;
  const cy = h / 2;
  const r = 122 * state.radarZoom;
  const rings = [0.25, 0.5, 0.75, 1];
  const angleFor = (i) => -Math.PI / 2 + (i * 2 * Math.PI) / axes.length;
  const point = (i, scale) => {
    const a = angleFor(i);
    return [cx + Math.cos(a) * r * scale, cy + Math.sin(a) * r * scale];
  };
  const pointForValue = (axis, i, val) => {
    const scale = val == null ? 0 : normalizedFromRange(val, axis.db.min, axis.db.max);
    return point(i, scale);
  };
  const valueOf = (stat) => stat?.avg ?? stat?.value;
  const pathForSeries = (item) => {
    const segments = [];
    for (let i = 0; i < axes.length; i += 1) {
      const j = (i + 1) % axes.length;
      const a = item.stats[axes[i].key];
      const b = item.stats[axes[j].key];
      if (!a || !b) continue;
      segments.push(`<line class="radar-segment" style="${item.style}" x1="${fmt(pointForValue(axes[i], i, valueOf(a))[0])}" y1="${fmt(pointForValue(axes[i], i, valueOf(a))[1])}" x2="${fmt(pointForValue(axes[j], j, valueOf(b))[0])}" y2="${fmt(pointForValue(axes[j], j, valueOf(b))[1])}"></line>`);
    }
    if (!item.missing) {
      const points = axes.map((axis, i) => pointForValue(axis, i, valueOf(item.stats[axis.key])).join(",")).join(" ");
      segments.unshift(`<polygon class="radar-fill" style="${item.style}" points="${points}"></polygon>`);
    }
    return segments.join("");
  };
  const grid = rings.map((ring) => `<polygon points="${axes.map((_, i) => point(i, ring).join(",")).join(" ")}" fill="none" stroke="var(--line)" stroke-width="1"/>`).join("");
  const spokes = axes.map((axis, i) => {
    const [x, y] = point(i, 1);
    const [lx, ly] = point(i, 1.18);
    const max = axis.max;
    const unit = formatUnit(axis.def.canonical_unit);
    const tip = [
      axis.def.label,
      `Database range: ${fmt(axis.db.min)}-${fmt(axis.db.max)} ${unit}`,
      max ? `Max: ${max.maxMaterial.product} / ${fmt(max.max)} ${unit}` : "",
    ].filter(Boolean).join("\n");
    return `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="var(--line)"/><text class="axis-label" data-tip="${escapeAttr(tip)}" x="${lx}" y="${ly}" text-anchor="${lx < cx - 10 ? "end" : lx > cx + 10 ? "start" : "middle"}">${escapeHtml(shortMetric(axis.def.label))}</text>`;
  }).join("");
  const seriesPoints = (item, index) => axes.map((axis, i) => {
    const stat = item.stats[axis.key];
    if (!stat) return "";
    const val = valueOf(stat);
    const [x, y] = pointForValue(axis, i, val);
    const unit = formatUnit(axis.def.canonical_unit || stat.unit || "");
    const valueText = stat.sample ? metricValueText(val, axis.def.canonical_unit || stat.unit || "", stat) : `${fmt(val)} ${unit}`;
    const tip = `${item.label}\n${axis.def.label}: ${valueText}\n${stat.count > 1 ? `range ${fmt(stat.min)}-${fmt(stat.max)} from ${stat.count} observations` : "single material value"}`;
    return `<circle class="radar-point" style="${item.style}" cx="${fmt(x)}" cy="${fmt(y)}" r="2.3" data-tip="${escapeAttr(tip)}"></circle>`;
  }).join("");
  const maxPoints = axes.map((axis, i) => {
    if (!axis.max) return "";
    const [x, y] = pointForValue(axis, i, axis.max.max);
    const unit = formatUnit(axis.def.canonical_unit || axis.max.unit || "");
    const tip = `${axis.def.label} max\n${axis.max.maxMaterial.product}\n${axis.max.maxMaterial.supplier} / ${fmt(axis.max.max)} ${unit}`;
    return `<circle class="radar-max-point" cx="${fmt(x)}" cy="${fmt(y)}" r="2.7" data-tip="${escapeAttr(tip)}"></circle>`;
  }).join("");
  return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Radar chart">${grid}${spokes}
    ${series.map(pathForSeries).join("")}
    ${series.map(seriesPoints).join("")}
    ${maxPoints}
  </svg>`;
}

async function loadManifestSources() {
  const paths = unique([
    appConfig.sourceManifestPath,
    "data/source_manifest.csv",
    "../filament_datasheets/_manifest/filament_datasheets.csv",
    "filament_datasheets/_manifest/filament_datasheets.csv",
  ].filter(Boolean));

  for (const path of paths) {
    try {
      const response = await fetch(withAssetVersion(path));
      if (!response.ok) continue;
      const rows = parseCsv(await response.text());
      if (!rows.length) continue;
      const header = rows[0];
      const index = new Map();
      for (const row of rows.slice(1)) {
        const item = Object.fromEntries(header.map((key, i) => [key, row[i] || ""]));
        if (item.local_path) index.set(normalizePath(item.local_path), item);
      }
      return index;
    } catch {
      continue;
    }
  }

  return new Map();
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (ch === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += ch;
    }
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows.filter((r) => r.some((v) => v !== ""));
}

function fillSelect(select, label, values) {
  const options = [];
  if (label !== "") options.push(`<option value="">${escapeHtml(label)}</option>`);
  for (const value of values) {
    if (Array.isArray(value)) {
      options.push(`<option value="${escapeAttr(value[0])}">${escapeHtml(value[1])}</option>`);
    } else {
      options.push(`<option value="${escapeAttr(value)}">${escapeHtml(value)}</option>`);
    }
  }
  select.innerHTML = options.join("");
}

function refreshPropertyScopeControls({ reset = false } = {}) {
  if (!state.data) return;
  if (els.advancedToggle) {
    els.advancedToggle.checked = state.advanced;
    els.advancedToggle.setAttribute("aria-valuetext", state.advanced ? "Advanced properties" : "Basic properties");
  }

  const propertyOptions = propertyOptionEntries();
  const previousProperty = els.propertyFilter.value;
  fillSelect(els.propertyFilter, "Any property", propertyOptions);
  els.propertyFilter.value = !reset && propertyOptions.some(([key]) => key === previousProperty) ? previousProperty : "";

  const numericProps = numericPropertyOptions();
  const numericKeys = new Set(numericProps.map(([key]) => key));
  const previousMapX = els.mapX.value;
  const previousMapY = els.mapY.value;
  fillSelect(els.mapX, "", numericProps);
  fillSelect(els.mapY, "", numericProps);
  els.mapX.value = !reset && numericKeys.has(previousMapX) ? previousMapX : numericKeys.has("density") ? "density" : numericProps[0]?.[0] || "";
  els.mapY.value = !reset && numericKeys.has(previousMapY) ? previousMapY : numericKeys.has("hdt") ? "hdt" : numericProps[1]?.[0] || numericProps[0]?.[0] || "";
  resetMapZoomState();

  const radarDefaults = propertyScopeKeys().filter((key) => numericKeys.has(key)).slice(0, 10);
  state.radarSelectedKeys = !reset
    ? state.radarSelectedKeys.filter((key) => numericKeys.has(key)).slice(0, 10)
    : radarDefaults;
  if (!state.radarSelectedKeys.length) state.radarSelectedKeys = radarDefaults;
  renderRadarAxisControls();
}

function propertyOptionEntries({ scoped = true } = {}) {
  const entries = [];
  const allowed = scoped && !state.advanced ? new Set(propertyScopeKeys()) : null;
  for (const prop of state.data?.properties || []) {
    if (!allowed || allowed.has(prop.key)) entries.push([prop.key, prop.label]);
    if (directionalPropertyKeys.has(prop.key)) {
      const xyKey = `${prop.key}::xy`;
      const zKey = `${prop.key}::z`;
      if (!allowed || allowed.has(xyKey)) entries.push([xyKey, `${prop.label} - XY / flat`]);
      if (!allowed || allowed.has(zKey)) entries.push([zKey, `${prop.label} - Z / vertical`]);
    }
  }
  return entries;
}

function numericPropertyOptions() {
  return propertyOptionEntries().filter(([key]) => {
    const range = dbMinMax(key);
    return Number.isFinite(range.min) && Number.isFinite(range.max) && range.max > range.min;
  });
}

function propertyScopeKeys() {
  if (state.advanced) return propertyOptionEntries({ scoped: false }).map(([key]) => key);
  return requestedBasicPropertyKeys.flatMap((key) => key === "impact_best" ? [bestImpactPropertyKey()] : [key]).filter(Boolean);
}

function bestImpactPropertyKey() {
  const candidates = ["impact_charpy", "impact_izod_area", "impact_izod", "impact_strength"];
  let best = "";
  let bestCount = -1;
  for (const key of candidates) {
    const count = numericObservationCount(key);
    if (count > bestCount) {
      best = key;
      bestCount = count;
    }
  }
  return best || "impact_charpy";
}

function numericObservationCount(key) {
  let count = 0;
  for (const material of state.materials || []) {
    for (const observation of material.observations || []) {
      if (observationMatchesProperty(observation, key) && typeof observation.value_nominal === "number") count += 1;
    }
  }
  return count;
}

function observationInPropertyScope(observation) {
  if (state.advanced) return true;
  return propertyScopeKeys().some((key) => observationMatchesProperty(observation, key));
}

function splitPropertyKey(key) {
  const [baseKey, orientation] = String(key || "").split("::");
  return { baseKey, orientation: orientation || "" };
}

function displayProp(key) {
  const { baseKey, orientation } = splitPropertyKey(key);
  const def = propDef(baseKey);
  if (!def) return { key, label: key, canonical_unit: "" };
  const suffix = orientation === "xy" ? " - XY / flat" : orientation === "z" ? " - Z / vertical" : "";
  return { ...def, key, baseKey, orientation, label: `${def.label}${suffix}` };
}

function orientationBucket(value) {
  const text = String(value || "").toLowerCase();
  if (!text) return "";
  if (/\bz\b|vertical|upright|up\b/.test(text)) return "z";
  if (/x-y|\bxy\b|horizontal|flat|side/.test(text)) return "xy";
  return "";
}

function orientationLabel(value) {
  const bucket = orientationBucket(value);
  if (bucket === "xy") return "XY";
  if (bucket === "z") return "Z";
  return "";
}

function observationMatchesProperty(observation, key) {
  const { baseKey, orientation } = splitPropertyKey(key);
  if (observation.property_key !== baseKey) return false;
  return !orientation || orientationBucket(observation.orientation) === orientation;
}

function selectedMaterial() {
  return materialById(state.selectedId);
}

function materialById(id) {
  return state.materials.find((m) => m.material_id === id) || null;
}

function propDef(key) {
  return state.data?.properties.find((p) => p.key === key) || null;
}

function sourceInfo(m) {
  return state.sourceIndex.get(normalizePath(m.source_file || "")) || {};
}

function localSourceHref(path) {
  return encodeURI(`../${normalizePath(path)}`);
}

function shouldShowLocalSourceLinks() {
  if (appConfig.showLocalSourceLinks) return true;
  const host = window.location.hostname;
  return window.location.protocol === "file:" || host === "localhost" || host === "127.0.0.1" || host === "::1";
}

function normalizePath(path) {
  return String(path || "").replace(/\\/g, "/");
}

function materialStat(m, key) {
  const vals = (m.observations || []).filter((o) => observationMatchesProperty(o, key) && typeof o.value_nominal === "number");
  if (!vals.length) return null;
  const avg = vals.reduce((sum, o) => sum + o.value_nominal, 0) / vals.length;
  const best = vals[0];
  const conversionSample = vals.find((o) => hasUnitConversion(o));
  return {
    value: avg,
    count: vals.length,
    unit: best.unit_canonical,
    sample: conversionSample || best,
    converted: Boolean(conversionSample),
    min: Math.min(...vals.map((o) => o.value_nominal)),
    max: Math.max(...vals.map((o) => o.value_nominal)),
  };
}

function metricTip(m, key, stat) {
  const def = displayProp(key);
  const bits = [
    `${m.product}`,
    `${def?.label || key}: ${metricValueText(stat.value, stat.unit || def?.canonical_unit || "", stat)}`,
    stat.count > 1 ? `Average of ${stat.count} extracted values; range ${fmt(stat.min)}-${fmt(stat.max)}.` : "Single extracted value.",
    [stat.sample.test_method, stat.sample.orientation, stat.sample.condition].filter(Boolean).join(" / "),
    ...qualityNotes(stat),
    stat.sample.source_context,
  ].filter(Boolean);
  return bits.join("\n");
}

function materialTip(m) {
  return `${m.product}\n${m.supplier} / ${m.base_material} / ${m.material_family}\n${m.observations.length} extracted observations\n${m.quality_notes || statusLabel(m.status)}`;
}

function fingerprintScores(m) {
  return fingerprintDefs.map((def) => {
    if (def.key === "printability") {
      const score = printabilityScore(m);
      return { ...def, score, tip: `Print ease heuristic: ${fmt(score * 100)}% based on nozzle, bed, chamber, and drying temperatures.` };
    }
    const stat = materialStat(m, def.key);
    const score = stat ? normalizedValue(def.key, stat.value) : def.fallback;
    return {
      ...def,
      score,
      tip: stat ? metricTip(m, def.key, stat) : `${def.label}: no extracted value, showing neutral placeholder.`,
    };
  });
}

function printabilityScore(m) {
  const nozzle = materialStat(m, "nozzle_temperature")?.value;
  const bed = materialStat(m, "bed_temperature")?.value;
  const chamber = materialStat(m, "chamber_temperature")?.value;
  const drying = materialStat(m, "drying_temperature")?.value;
  const base = (m.base_material || "").toUpperCase();
  let score = 0.82;
  if (["PLA", "PETG", "PVB"].includes(base)) score += 0.08;
  if (["PEEK", "PEI", "PEKK", "PPS", "PPSU", "PSU"].includes(base)) score -= 0.22;
  if (base.startsWith("PA")) score -= 0.14;
  if (Number.isFinite(nozzle)) score -= normalizedFromRange(nozzle, 180, 445) * 0.22;
  if (Number.isFinite(bed)) score -= normalizedFromRange(bed, 0, 140) * 0.12;
  if (Number.isFinite(chamber) && chamber > 40) score -= 0.12;
  if (Number.isFinite(drying) && drying > 65) score -= 0.08;
  return clamp(score, 0.08, 0.98);
}

function normalizedValue(key, value) {
  const range = dbMinMax(key);
  return normalizedFromRange(value, range.min, range.max);
}

function normalizedFromRange(value, min, max) {
  if (!Number.isFinite(value) || !Number.isFinite(min) || !Number.isFinite(max) || max <= min) return 0;
  return clamp((value - min) / (max - min), 0, 1);
}

function dbMinMax(key) {
  const { baseKey, orientation } = splitPropertyKey(key);
  if (!orientation) {
    const cov = state.data.summary.coverage.find((c) => c.property_key === baseKey);
    return { min: cov?.min ?? 0, max: cov?.max ?? 1 };
  }
  const values = [];
  for (const material of state.materials || []) {
    for (const observation of material.observations || []) {
      if (observationMatchesProperty(observation, key) && typeof observation.value_nominal === "number") {
        values.push(observation.value_nominal);
      }
    }
  }
  return values.length ? { min: Math.min(...values), max: Math.max(...values) } : { min: 0, max: 0 };
}

function summarizeGroup(materials) {
  const out = {};
  for (const m of materials) {
    for (const o of m.observations) {
      if (typeof o.value_nominal !== "number") continue;
      if (!out[o.property_key]) out[o.property_key] = [];
      out[o.property_key].push(o.value_nominal);
    }
  }
  return Object.fromEntries(Object.entries(out).map(([key, vals]) => [key, {
    count: vals.length,
    min: Math.min(...vals),
    max: Math.max(...vals),
    avg: vals.reduce((a, b) => a + b, 0) / vals.length,
  }]));
}

function statForMaterials(materials, key) {
  const rows = [];
  for (const material of materials || []) {
    for (const observation of material.observations || []) {
      if (!observationMatchesProperty(observation, key) || typeof observation.value_nominal !== "number") continue;
      rows.push({ material, observation, value: observation.value_nominal });
    }
  }
  if (!rows.length) return null;
  const values = rows.map((row) => row.value);
  const sorted = [...values].sort((a, b) => a - b);
  const maxRow = rows.reduce((best, row) => (row.value > best.value ? row : best), rows[0]);
  const minRow = rows.reduce((best, row) => (row.value < best.value ? row : best), rows[0]);
  return {
    count: rows.length,
    min: Math.min(...values),
    max: Math.max(...values),
    avg: values.reduce((a, b) => a + b, 0) / values.length,
    median: percentile(sorted, 0.5),
    q1: percentile(sorted, 0.25),
    q3: percentile(sorted, 0.75),
    unit: rows[0].observation.unit_canonical,
    maxMaterial: maxRow.material,
    maxObservation: maxRow.observation,
    minMaterial: minRow.material,
    minObservation: minRow.observation,
    converted: rows.some((row) => hasUnitConversion(row.observation)),
  };
}

function percentile(sortedValues, p) {
  if (!sortedValues.length) return null;
  if (sortedValues.length === 1) return sortedValues[0];
  const index = (sortedValues.length - 1) * p;
  const lo = Math.floor(index);
  const hi = Math.ceil(index);
  const weight = index - lo;
  return sortedValues[lo] * (1 - weight) + sortedValues[hi] * weight;
}

function uniqueObservations(observations) {
  const seen = new Set();
  const out = [];
  for (const o of observations || []) {
    const key = [o.property_key, o.value_nominal, o.raw_value, o.unit_canonical, o.test_method, o.orientation, o.condition].join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(o);
  }
  return out;
}

function groupBy(items, fn) {
  return items.reduce((acc, item) => {
    const key = fn(item);
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});
}

function unique(values) {
  return [...new Set(values.filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b)));
}

function colorStyle(value, scope = "base", baseHint = "") {
  const { hue, sat } = colorToken(value, scope, baseHint);
  return `--mat-h:${hue};--mat-s:${sat}%;`;
}

function colorToken(value, scope = "base", baseHint = "") {
  const raw = String(value || "Unknown");
  const key = raw.toUpperCase();
  if (scope === "base" && basePalette[key]) return { hue: basePalette[key][0], sat: basePalette[key][1] };
  if (scope === "family" && baseHint && basePalette[String(baseHint).toUpperCase()]) {
    const base = basePalette[String(baseHint).toUpperCase()];
    const offset = (hashString(raw) % 37) - 18;
    return { hue: modHue(base[0] + offset), sat: clamp(base[1] + ((hashString(raw + "s") % 15) - 7), 46, 78) };
  }
  const hash = hashString(raw);
  return { hue: modHue(23 + hash * 137.508), sat: 52 + (hash % 24) };
}

function hashString(value) {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function modHue(value) {
  return Math.round(((value % 360) + 360) % 360);
}

function initTooltip() {
  let active = null;
  document.addEventListener("mouseover", (event) => {
    const target = event.target.closest?.("[data-tip]");
    if (!target) return;
    active = target;
    els.tooltip.textContent = target.getAttribute("data-tip");
    els.tooltip.hidden = false;
    moveTooltip(event);
  });
  document.addEventListener("mousemove", (event) => {
    if (active) moveTooltip(event);
  });
  document.addEventListener("mouseout", (event) => {
    if (active && !event.relatedTarget?.closest?.("[data-tip]")) {
      active = null;
      els.tooltip.hidden = true;
    }
  });
}

function moveTooltip(event) {
  const pad = 14;
  const rect = els.tooltip.getBoundingClientRect();
  let x = event.clientX + 14;
  let y = event.clientY + 14;
  if (x + rect.width + pad > window.innerWidth) x = event.clientX - rect.width - 14;
  if (y + rect.height + pad > window.innerHeight) y = event.clientY - rect.height - 14;
  els.tooltip.style.left = `${Math.max(pad, x)}px`;
  els.tooltip.style.top = `${Math.max(pad, y)}px`;
}

function refreshIcons() {
  if (window.lucide?.createIcons) {
    window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
  }
}

function categorySort(a, b) {
  const order = ["Filament specs", "Print settings", "Mechanical", "Thermal", "Physical", "Electrical", "Safety / chemical", "Other"];
  return (order.indexOf(a) === -1 ? 99 : order.indexOf(a)) - (order.indexOf(b) === -1 ? 99 : order.indexOf(b)) || a.localeCompare(b);
}

function statusLabel(status) {
  return String(status || "unknown").replace(/_/g, " ");
}

function shortMetric(label) {
  return String(label || "")
    .replace(" / ", "/")
    .replace(" temperature", "")
    .replace(" strength", "")
    .replace("Heat deflection / distortion", "HDT")
    .replace("Nozzle / extruder", "Nozzle")
    .replace("Bed / build plate", "Bed")
    .replace("Tensile", "Tensile")
    .replace("Density / specific gravity", "Density")
    .replace("Elongation / strain", "Elongation")
    .replace("Tensile / Young's modulus", "Modulus");
}

function shortProduct(product) {
  const text = String(product || "");
  return text.length > 18 ? `${text.slice(0, 17)}...` : text;
}

function pct(value) {
  return Math.max(3, Math.min(100, value * 100));
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function fmt(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "";
  if (typeof value === "string") return value;
  if (Math.abs(value) >= 1000) return value.toFixed(0);
  if (Math.abs(value) >= 100) return value.toFixed(1);
  if (Math.abs(value) >= 10) return value.toFixed(2);
  return value.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
}

function fmtInt(value) {
  return new Intl.NumberFormat().format(value || 0);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[ch]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}
