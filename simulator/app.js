const materials = {
  PLA: { e: 3200, strength: 58 },
  PETG: { e: 2100, strength: 50 },
  ABS: { e: 1900, strength: 38 },
  Custom: { e: 2500, strength: 45 },
};

const scenarios = {
  optimistic: { label: "Optimistic", e: 1, allow: 0.75 },
  realistic: { label: "Realistic", e: 0.75, allow: 0.45 },
  pessimistic: { label: "Pessimistic", e: 0.55, allow: 0.25 },
};

const directionFactors = {
  along: { e: 1, allow: 1, label: "Roads along span" },
  mixed: { e: 0.85, allow: 0.8, label: "Mixed roads" },
  across: { e: 0.7, allow: 0.7, label: "Roads across span" },
};

const presets = {
  beam: {
    thickness: 6,
    points: [
      [0, 0],
      [140, 0],
      [140, 20],
      [0, 20],
    ],
    supports: [
      { id: "s1", type: "pinned", x: 0 },
      { id: "s2", type: "roller", x: 140 },
    ],
    loads: [{ id: "p1", type: "point", x: 70, force: 80 }],
  },
  notched: {
    thickness: 6,
    points: [
      [0, 0],
      [150, 0],
      [150, 24],
      [92, 24],
      [92, 14],
      [66, 14],
      [66, 24],
      [0, 24],
    ],
    supports: [
      { id: "s1", type: "pinned", x: 0 },
      { id: "s2", type: "roller", x: 150 },
    ],
    loads: [{ id: "p1", type: "point", x: 75, force: 90 }],
  },
  tapered: {
    thickness: 5,
    points: [
      [0, 0],
      [150, 5],
      [150, 24],
      [0, 34],
    ],
    supports: [
      { id: "s1", type: "fixed", x: 0 },
    ],
    loads: [{ id: "p1", type: "point", x: 145, force: 55 }],
  },
  bracket: {
    thickness: 6,
    points: [
      [0, 0],
      [95, 0],
      [95, 18],
      [36, 18],
      [36, 58],
      [0, 58],
    ],
    supports: [
      { id: "s1", type: "fixed", x: 0 },
    ],
    loads: [{ id: "p1", type: "point", x: 88, force: 70 }],
  },
};

const state = {
  preset: "beam",
  tool: "edit",
  grid: 1,
  zoom: 1,
  panX: 0,
  panY: 0,
  sliceZoom: 1,
  slicePanX: 0,
  slicePanY: 0,
  activeScenario: "realistic",
  sectionPct: 50,
  materialPreset: "PLA",
  materialE: 3200,
  materialStrength: 58,
  printDirection: "along",
  thickness: 6,
  points: [],
  supports: [],
  loads: [],
  drawPoints: [],
  pendingUdlStart: null,
  draggingVertex: null,
  panning: null,
  results: null,
  solveVersion: 0,
  lastViewBox: [0, 0, 1, 1],
  showStress: true,
  showDeflection: true,
  showMesh: false,
};

const els = {
  solveStatus: document.getElementById("solveStatus"),
  runSolve: document.getElementById("runSolve"),
  materialScenarioNote: document.getElementById("materialScenarioNote"),
  materialPreset: document.getElementById("materialPreset"),
  materialE: document.getElementById("materialE"),
  materialStrength: document.getElementById("materialStrength"),
  printDirection: document.getElementById("printDirection"),
  presetButtons: document.getElementById("presetButtons"),
  gridStep: document.getElementById("gridStep"),
  gridReadout: document.getElementById("gridReadout"),
  thickness: document.getElementById("thickness"),
  zoom: document.getElementById("zoom"),
  zoomOut: document.getElementById("zoomOut"),
  zoomIn: document.getElementById("zoomIn"),
  panUp: document.getElementById("panUp"),
  panDown: document.getElementById("panDown"),
  panLeft: document.getElementById("panLeft"),
  panRight: document.getElementById("panRight"),
  resetView: document.getElementById("resetView"),
  toolButtons: document.getElementById("toolButtons"),
  toolLabel: document.getElementById("toolLabel"),
  closePolygon: document.getElementById("closePolygon"),
  cancelDraw: document.getElementById("cancelDraw"),
  supportType: document.getElementById("supportType"),
  supportX: document.getElementById("supportX"),
  addSupport: document.getElementById("addSupport"),
  pointX: document.getElementById("pointX"),
  pointForce: document.getElementById("pointForce"),
  addPointLoad: document.getElementById("addPointLoad"),
  udlStart: document.getElementById("udlStart"),
  udlEnd: document.getElementById("udlEnd"),
  udlMag: document.getElementById("udlMag"),
  addUdl: document.getElementById("addUdl"),
  loadCount: document.getElementById("loadCount"),
  loadList: document.getElementById("loadList"),
  canvasHint: document.getElementById("canvasHint"),
  showStress: document.getElementById("showStress"),
  showDeflection: document.getElementById("showDeflection"),
  showMesh: document.getElementById("showMesh"),
  modelSvg: document.getElementById("modelSvg"),
  deflectionDiagram: document.getElementById("deflectionDiagram"),
  stressDiagram: document.getElementById("stressDiagram"),
  momentDiagram: document.getElementById("momentDiagram"),
  shearDiagram: document.getElementById("shearDiagram"),
  deflectionPeak: document.getElementById("deflectionPeak"),
  stressPeak: document.getElementById("stressPeak"),
  momentPeak: document.getElementById("momentPeak"),
  shearPeak: document.getElementById("shearPeak"),
  scenarioButtons: document.getElementById("scenarioButtons"),
  activeScenarioLabel: document.getElementById("activeScenarioLabel"),
  metricList: document.getElementById("metricList"),
  riskBands: document.getElementById("riskBands"),
  sectionSlider: document.getElementById("sectionSlider"),
  sectionXLabel: document.getElementById("sectionXLabel"),
  sectionView: document.getElementById("sectionView"),
  sliceLayerDown: document.getElementById("sliceLayerDown"),
  sliceLayerUp: document.getElementById("sliceLayerUp"),
  sliceZoomOut: document.getElementById("sliceZoomOut"),
  sliceZoomIn: document.getElementById("sliceZoomIn"),
  slicePanUp: document.getElementById("slicePanUp"),
  slicePanDown: document.getElementById("slicePanDown"),
  slicePanLeft: document.getElementById("slicePanLeft"),
  slicePanRight: document.getElementById("slicePanRight"),
  sliceReset: document.getElementById("sliceReset"),
  layerHeight: document.getElementById("layerHeight"),
  lineWidth: document.getElementById("lineWidth"),
  perimeters: document.getElementById("perimeters"),
  itemCount: document.getElementById("itemCount"),
  itemList: document.getElementById("itemList"),
  toast: document.getElementById("toast"),
};

init();

function init() {
  loadPreset("beam");
  attachEvents();
  solveAndRender("Initial solve");
  refreshIcons();
  window.fdmSimTest = {
    getState: () => JSON.parse(JSON.stringify({
      tool: state.tool,
      grid: state.grid,
      zoom: state.zoom,
      panX: state.panX,
      panY: state.panY,
      activeScenario: state.activeScenario,
      points: state.points,
      supports: state.supports,
      loads: state.loads,
      results: summarizeResultsForTest(),
    })),
  };
}

function attachEvents() {
  els.runSolve.addEventListener("click", () => solveAndRender("Solved"));

  els.materialPreset.addEventListener("change", () => {
    state.materialPreset = els.materialPreset.value;
    if (materials[state.materialPreset]) {
      state.materialE = materials[state.materialPreset].e;
      state.materialStrength = materials[state.materialPreset].strength;
      els.materialE.value = state.materialE;
      els.materialStrength.value = state.materialStrength;
    }
    solveAndRender("Material updated");
  });

  for (const input of [els.materialE, els.materialStrength]) {
    input.addEventListener("input", () => {
      state.materialPreset = "Custom";
      els.materialPreset.value = "Custom";
      state.materialE = positiveNumber(els.materialE.value, state.materialE);
      state.materialStrength = positiveNumber(els.materialStrength.value, state.materialStrength);
      solveAndRender("Material updated");
    });
  }

  els.printDirection.addEventListener("change", () => {
    state.printDirection = els.printDirection.value;
    solveAndRender("Print direction updated");
  });

  els.presetButtons.addEventListener("click", (event) => {
    const button = event.target.closest("[data-preset]");
    if (!button) return;
    loadPreset(button.dataset.preset);
    setTool("edit");
    solveAndRender("Preset loaded");
  });

  els.gridStep.addEventListener("change", () => {
    state.grid = Number(els.gridStep.value) || 1;
    state.points = state.points.map(([x, y]) => snapPoint(x, y));
    state.supports = state.supports.map((support) => ({ ...support, x: snapScalar(support.x) }));
    state.loads = state.loads.map((load) => load.type === "point"
      ? { ...load, x: snapScalar(load.x) }
      : { ...load, x1: snapScalar(load.x1), x2: snapScalar(load.x2) });
    solveAndRender("Grid updated");
  });

  els.thickness.addEventListener("input", () => {
    state.thickness = positiveNumber(els.thickness.value, state.thickness);
    solveAndRender("Thickness updated");
  });

  els.zoom.addEventListener("input", () => {
    state.zoom = Number(els.zoom.value) || 1;
    renderAll();
  });

  els.zoomOut.addEventListener("click", () => stepZoom(-0.15));
  els.zoomIn.addEventListener("click", () => stepZoom(0.15));
  els.panUp.addEventListener("click", () => stepPan(0, -0.18));
  els.panDown.addEventListener("click", () => stepPan(0, 0.18));
  els.panLeft.addEventListener("click", () => stepPan(-0.18, 0));
  els.panRight.addEventListener("click", () => stepPan(0.18, 0));
  els.resetView.addEventListener("click", resetMainView);

  els.toolButtons.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tool]");
    if (!button) return;
    setTool(button.dataset.tool);
  });

  els.closePolygon.addEventListener("click", () => {
    if (state.drawPoints.length < 3) {
      toast("Draw at least three points before closing the shape.");
      return;
    }
    state.points = normalizePolygon(clonePoints(state.drawPoints));
    state.drawPoints = [];
    setTool("edit");
    fitSupportsAndLoadsToGeometry();
    solveAndRender("Shape closed");
  });

  els.cancelDraw.addEventListener("click", () => {
    state.drawPoints = [];
    renderAll();
  });

  els.addSupport.addEventListener("click", () => {
    addSupport(Number(els.supportX.value), els.supportType.value);
    solveAndRender("Support added");
  });

  els.addPointLoad.addEventListener("click", () => {
    addPointLoad(Number(els.pointX.value), Number(els.pointForce.value));
    solveAndRender("Point load added");
  });

  els.addUdl.addEventListener("click", () => {
    addUdl(Number(els.udlStart.value), Number(els.udlEnd.value), Number(els.udlMag.value));
    solveAndRender("UDL added");
  });

  for (const input of [els.showStress, els.showDeflection, els.showMesh]) {
    input.addEventListener("change", () => {
      state.showStress = els.showStress.checked;
      state.showDeflection = els.showDeflection.checked;
      state.showMesh = els.showMesh.checked;
      renderAll();
    });
  }

  els.modelSvg.addEventListener("pointerdown", onSvgPointerDown);
  window.addEventListener("pointermove", onSvgPointerMove);
  window.addEventListener("pointerup", onSvgPointerUp);

  els.scenarioButtons.addEventListener("click", (event) => {
    const button = event.target.closest("[data-scenario]");
    if (!button) return;
    state.activeScenario = button.dataset.scenario;
    renderAll();
  });

  els.sectionSlider.addEventListener("input", () => {
    state.sectionPct = Number(els.sectionSlider.value) || 0;
    renderAll();
  });

  els.sliceLayerDown.addEventListener("click", () => stepSliceLayer(-1));
  els.sliceLayerUp.addEventListener("click", () => stepSliceLayer(1));
  els.sliceZoomOut.addEventListener("click", () => stepSliceZoom(-0.2));
  els.sliceZoomIn.addEventListener("click", () => stepSliceZoom(0.2));
  els.slicePanUp.addEventListener("click", () => stepSlicePan(0, -0.14));
  els.slicePanDown.addEventListener("click", () => stepSlicePan(0, 0.14));
  els.slicePanLeft.addEventListener("click", () => stepSlicePan(-0.14, 0));
  els.slicePanRight.addEventListener("click", () => stepSlicePan(0.14, 0));
  els.sliceReset.addEventListener("click", resetSliceView);

  for (const input of [els.layerHeight, els.lineWidth, els.perimeters]) {
    input.addEventListener("input", renderSectionView);
  }

  els.itemList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-delete]");
    if (!button) return;
    const [kind, id] = button.dataset.delete.split(":");
    if (kind === "support") state.supports = state.supports.filter((item) => item.id !== id);
    if (kind === "load") state.loads = state.loads.filter((item) => item.id !== id);
    solveAndRender("Item deleted");
  });

  els.loadList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-delete]");
    if (!button) return;
    const [, id] = button.dataset.delete.split(":");
    state.loads = state.loads.filter((item) => item.id !== id);
    solveAndRender("Load deleted");
  });
}

function loadPreset(name) {
  const preset = presets[name] || presets.beam;
  state.preset = name in presets ? name : "beam";
  state.thickness = preset.thickness;
  state.points = clonePoints(preset.points);
  state.supports = preset.supports.map((support) => ({ ...support }));
  state.loads = preset.loads.map((load) => ({ ...load }));
  state.drawPoints = [];
  state.pendingUdlStart = null;
  state.panX = 0;
  state.panY = 0;
  state.slicePanX = 0;
  state.slicePanY = 0;
  state.sliceZoom = 1;
  state.sectionPct = 50;
  els.sectionSlider.value = "50";
  els.thickness.value = state.thickness;
  els.presetButtons.querySelectorAll("[data-preset]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.preset === state.preset);
  });
}

function setTool(tool) {
  state.tool = tool;
  state.pendingUdlStart = null;
  els.toolButtons.querySelectorAll("[data-tool]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.tool === tool);
  });
  const labels = {
    edit: "Edit",
    draw: "Draw",
    support: "Support",
    pointLoad: "Point",
    udl: "UDL",
    pan: "Pan",
  };
  els.toolLabel.textContent = labels[tool] || "Edit";
  els.canvasHint.textContent = toolHint(tool);
  renderAll();
}

function stepZoom(delta) {
  const min = Number(els.zoom.min) || 0.65;
  const max = Number(els.zoom.max) || 2.8;
  const next = clamp((Number(els.zoom.value) || state.zoom) + delta, min, max);
  state.zoom = next;
  els.zoom.value = String(next);
  renderAll();
}

function stepPan(dxFraction, dyFraction) {
  const [, , width, height] = state.lastViewBox;
  state.panX += width * dxFraction;
  state.panY += height * dyFraction;
  renderAll();
}

function resetMainView() {
  state.panX = 0;
  state.panY = 0;
  state.zoom = 1;
  els.zoom.value = "1";
  renderAll();
}

function stepSliceLayer(direction) {
  const bounds = polygonBounds(state.points);
  const height = Math.max(1, bounds.maxY - bounds.minY);
  const layerHeight = positiveNumber(els.layerHeight.value, 0.2);
  const pctStep = (layerHeight / height) * 100 * direction;
  state.sectionPct = clamp(state.sectionPct + pctStep, 0, 100);
  els.sectionSlider.value = String(state.sectionPct);
  renderAll();
}

function stepSliceZoom(delta) {
  state.sliceZoom = clamp(state.sliceZoom + delta, 0.6, 4);
  renderSectionView();
}

function stepSlicePan(dxFraction, dyFraction) {
  const bounds = polygonBounds(state.points);
  const span = Math.max(1, bounds.maxX - bounds.minX);
  const height = Math.max(1, bounds.maxY - bounds.minY);
  state.slicePanX += span * dxFraction / state.sliceZoom;
  state.slicePanY += height * dyFraction / state.sliceZoom;
  renderSectionView();
}

function resetSliceView() {
  state.sliceZoom = 1;
  state.slicePanX = 0;
  state.slicePanY = 0;
  renderSectionView();
}

function solveAndRender(message) {
  state.solveVersion += 1;
  const started = performance.now();
  state.results = solveAllScenarios();
  const elapsed = Math.max(1, Math.round(performance.now() - started));
  const active = activeResult();
  els.solveStatus.textContent = active?.error ? "Check model" : `${message} (${elapsed} ms)`;
  renderAll();
}

function solveAllScenarios() {
  const out = {};
  for (const key of Object.keys(scenarios)) {
    out[key] = solveScenario(key);
  }
  return out;
}

function solveScenario(key) {
  const bounds = polygonBounds(state.points);
  const span = bounds.maxX - bounds.minX;
  if (!Number.isFinite(span) || span <= 1) return { error: "Draw a shape with nonzero span." };
  if (state.supports.length === 0) return { error: "Add at least one support." };
  const n = Math.max(36, Math.min(130, Math.round(span / 1.5)));
  const nodes = [];
  for (let i = 0; i <= n; i += 1) {
    const x = bounds.minX + (span * i) / n;
    const section = verticalSections(state.points, safeSectionX(x, bounds));
    const height = Math.max(0.2, section.total);
    nodes.push({
      x,
      section,
      height,
      yCenter: section.center,
      area: state.thickness * height,
      inertia: (state.thickness * Math.pow(height, 3)) / 12,
    });
  }

  const scenario = scenarios[key];
  const direction = directionFactors[state.printDirection] || directionFactors.mixed;
  const e = Math.max(1, state.materialE * scenario.e * direction.e);
  const allowable = Math.max(0.1, state.materialStrength * scenario.allow * direction.allow);
  const dof = nodes.length * 2;
  const k = Array.from({ length: dof }, () => Array(dof).fill(0));
  const f = Array(dof).fill(0);

  for (let i = 0; i < nodes.length - 1; i += 1) {
    const a = nodes[i];
    const b = nodes[i + 1];
    const le = b.x - a.x;
    const inertia = Math.max(0.001, (a.inertia + b.inertia) / 2);
    const ei = e * inertia;
    const ke = beamElementStiffness(ei, le);
    const idx = [2 * i, 2 * i + 1, 2 * (i + 1), 2 * (i + 1) + 1];
    addMatrix(k, ke, idx);
  }

  for (const load of state.loads) {
    if (load.type === "point") {
      const i = nearestNode(nodes, load.x);
      f[2 * i] += Math.max(-100000, Math.min(100000, load.force));
    } else {
      applyDistributedLoad(f, nodes, load);
    }
  }

  const constrained = new Set();
  for (const support of state.supports) {
    const i = nearestNode(nodes, support.x);
    constrained.add(2 * i);
    if (support.type === "fixed") constrained.add(2 * i + 1);
  }

  if (constrained.size < 2 && ![...constrained].some((d) => d % 2 === 1)) {
    return { error: "Model is under-constrained. Add another vertical support or a fixed support.", nodes };
  }

  const free = [];
  for (let i = 0; i < dof; i += 1) {
    if (!constrained.has(i)) free.push(i);
  }

  try {
    const kr = free.map((r) => free.map((c) => k[r][c]));
    const fr = free.map((r) => f[r]);
    const ur = solveLinearSystem(kr, fr);
    const u = Array(dof).fill(0);
    free.forEach((dofIndex, i) => {
      u[dofIndex] = ur[i];
    });
    return postProcess(nodes, u, e, allowable, key);
  } catch (error) {
    return { error: "Solver could not resolve the model. Check supports and geometry.", nodes };
  }
}

function postProcess(nodes, u, e, allowable, scenarioKey) {
  const stations = [];
  let maxDeflection = 0;
  let maxStress = 0;
  let maxMoment = 0;
  let maxShear = 0;
  let maxUtil = 0;
  for (let i = 0; i < nodes.length; i += 1) {
    maxDeflection = Math.max(maxDeflection, Math.abs(u[2 * i]));
  }

  for (let i = 0; i < nodes.length - 1; i += 1) {
    const a = nodes[i];
    const b = nodes[i + 1];
    const le = b.x - a.x;
    const d = [u[2 * i], u[2 * i + 1], u[2 * (i + 1)], u[2 * (i + 1) + 1]];
    for (const r of [0, 0.5, 1]) {
      const x = a.x + le * r;
      const section = verticalSections(state.points, safeSectionX(x, polygonBounds(state.points)));
      const height = Math.max(0.2, section.total);
      const inertia = (state.thickness * Math.pow(height, 3)) / 12;
      const area = state.thickness * height;
      const curvature = elementCurvature(d, le, r);
      const third = elementThirdDerivative(d, le);
      const moment = e * inertia * curvature;
      const shear = e * inertia * third;
      const kt = concentrationMultiplier(nodes, i);
      const bendingStress = Math.abs(moment) * (height / 2) / Math.max(0.001, inertia);
      const shearStress = 1.5 * Math.abs(shear) / Math.max(0.001, area);
      const stress = kt * Math.max(bendingStress, shearStress);
      const util = stress / allowable;
      maxStress = Math.max(maxStress, stress);
      maxMoment = Math.max(maxMoment, Math.abs(moment));
      maxShear = Math.max(maxShear, Math.abs(shear));
      maxUtil = Math.max(maxUtil, util);
      stations.push({
        x,
        deflection: interpolateElementDeflection(d, le, r),
        moment,
        shear,
        stress,
        util,
        height,
        yCenter: section.center,
        kt,
      });
    }
  }

  return {
    scenarioKey,
    e,
    allowable,
    nodes,
    u,
    stations,
    maxDeflection,
    maxStress,
    maxMoment,
    maxShear,
    maxUtil,
  };
}

function beamElementStiffness(ei, l) {
  const l2 = l * l;
  const l3 = l2 * l;
  return [
    [12 * ei / l3, 6 * ei / l2, -12 * ei / l3, 6 * ei / l2],
    [6 * ei / l2, 4 * ei / l, -6 * ei / l2, 2 * ei / l],
    [-12 * ei / l3, -6 * ei / l2, 12 * ei / l3, -6 * ei / l2],
    [6 * ei / l2, 2 * ei / l, -6 * ei / l2, 4 * ei / l],
  ];
}

function addMatrix(target, local, idx) {
  for (let r = 0; r < idx.length; r += 1) {
    for (let c = 0; c < idx.length; c += 1) {
      target[idx[r]][idx[c]] += local[r][c];
    }
  }
}

function applyDistributedLoad(f, nodes, load) {
  const x1 = Math.min(load.x1, load.x2);
  const x2 = Math.max(load.x1, load.x2);
  const w = Math.max(-10000, Math.min(10000, load.w));
  for (let i = 0; i < nodes.length - 1; i += 1) {
    const a = nodes[i].x;
    const b = nodes[i + 1].x;
    const overlap = Math.max(0, Math.min(b, x2) - Math.max(a, x1));
    if (overlap <= 0) continue;
    const le = b - a;
    const q = w * (overlap / le);
    f[2 * i] += q * le / 2;
    f[2 * i + 1] += q * le * le / 12;
    f[2 * (i + 1)] += q * le / 2;
    f[2 * (i + 1) + 1] -= q * le * le / 12;
  }
}

function interpolateElementDeflection(d, l, r) {
  const n1 = 1 - 3 * r * r + 2 * r * r * r;
  const n2 = l * (r - 2 * r * r + r * r * r);
  const n3 = 3 * r * r - 2 * r * r * r;
  const n4 = l * (-r * r + r * r * r);
  return n1 * d[0] + n2 * d[1] + n3 * d[2] + n4 * d[3];
}

function elementCurvature(d, l, r) {
  return ((-6 + 12 * r) / (l * l)) * d[0]
    + ((-4 + 6 * r) / l) * d[1]
    + ((6 - 12 * r) / (l * l)) * d[2]
    + ((-2 + 6 * r) / l) * d[3];
}

function elementThirdDerivative(d, l) {
  return (12 / Math.pow(l, 3)) * d[0]
    + (6 / (l * l)) * d[1]
    + (-12 / Math.pow(l, 3)) * d[2]
    + (6 / (l * l)) * d[3];
}

function concentrationMultiplier(nodes, i) {
  const prev = nodes[Math.max(0, i - 1)]?.height || nodes[i].height;
  const here = nodes[i].height;
  const next = nodes[Math.min(nodes.length - 1, i + 1)]?.height || here;
  const dx = Math.max(1, Math.abs((nodes[Math.min(nodes.length - 1, i + 1)]?.x || nodes[i].x) - (nodes[Math.max(0, i - 1)]?.x || nodes[i].x)));
  const slope = Math.abs(next - prev) / dx;
  return 1 + Math.min(1.4, slope * 3.2 + (Math.abs(next - here) > here * 0.22 ? 0.35 : 0));
}

function solveLinearSystem(a, b) {
  const n = b.length;
  const m = a.map((row, i) => [...row, b[i]]);
  for (let i = 0; i < n; i += 1) {
    let pivot = i;
    for (let r = i + 1; r < n; r += 1) {
      if (Math.abs(m[r][i]) > Math.abs(m[pivot][i])) pivot = r;
    }
    if (Math.abs(m[pivot][i]) < 1e-9) throw new Error("Singular matrix");
    if (pivot !== i) [m[i], m[pivot]] = [m[pivot], m[i]];
    const diag = m[i][i];
    for (let c = i; c <= n; c += 1) m[i][c] /= diag;
    for (let r = 0; r < n; r += 1) {
      if (r === i) continue;
      const factor = m[r][i];
      if (Math.abs(factor) < 1e-14) continue;
      for (let c = i; c <= n; c += 1) m[r][c] -= factor * m[i][c];
    }
  }
  return m.map((row) => row[n]);
}

function renderAll() {
  renderControls();
  renderModel();
  renderResults();
  renderDiagrams();
  renderSectionView();
  renderItems();
  renderLoadList();
  refreshIcons();
}

function renderControls() {
  els.gridReadout.textContent = `${fmt(state.grid)} mm snap`;
  els.materialScenarioNote.textContent = scenarios[state.activeScenario].label;
  els.activeScenarioLabel.textContent = scenarios[state.activeScenario].label;
  els.modelSvg.classList.toggle("is-panning", state.tool === "pan");
  els.scenarioButtons.querySelectorAll("[data-scenario]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.scenario === state.activeScenario);
  });
  els.closePolygon.disabled = state.drawPoints.length < 3;
}

function renderModel() {
  const bounds = paddedBounds(state.points, state.zoom);
  bounds.minX += state.panX;
  bounds.maxX += state.panX;
  bounds.minY += state.panY;
  bounds.maxY += state.panY;
  state.lastViewBox = [bounds.minX, bounds.minY, bounds.maxX - bounds.minX, bounds.maxY - bounds.minY];
  els.modelSvg.setAttribute("viewBox", state.lastViewBox.map((v) => fmt(v)).join(" "));
  const active = activeResult();
  els.modelSvg.innerHTML = [
    svgDefs(),
    renderGrid(bounds),
    renderStressShape(active),
    renderMesh(active),
    renderNeutralLine(active),
    renderDeformedLine(active),
    renderDrawDraft(),
    renderSupports(),
    renderLoads(),
    renderSectionProbe(),
    renderVertices(),
    renderAxes(bounds),
  ].join("");
}

function renderGrid(bounds) {
  const lines = [];
  const step = state.grid;
  const x0 = Math.floor(bounds.minX / step) * step;
  const y0 = Math.floor(bounds.minY / step) * step;
  for (let x = x0; x <= bounds.maxX + step; x += step) {
    lines.push(`<line class="grid-line${isMajor(x) ? " major" : ""}" x1="${fmt(x)}" y1="${fmt(bounds.minY)}" x2="${fmt(x)}" y2="${fmt(bounds.maxY)}"></line>`);
  }
  for (let y = y0; y <= bounds.maxY + step; y += step) {
    lines.push(`<line class="grid-line${isMajor(y) ? " major" : ""}" x1="${fmt(bounds.minX)}" y1="${fmt(y)}" x2="${fmt(bounds.maxX)}" y2="${fmt(y)}"></line>`);
  }
  return `<g>${lines.join("")}</g>`;
}

function renderStressShape(active) {
  const bounds = polygonBounds(state.points);
  const baseShape = `<polygon class="shape-fill" fill="${utilColor(0.2)}" points="${pointString(state.points)}"></polygon>
      <polyline class="shape-outline" points="${closedPointString(state.points)}"></polyline>`;
  if (!state.showStress || !active || active.error) {
    return baseShape;
  }
  const stations = active.stations || [];
  if (!stations.length || bounds.maxX <= bounds.minX || bounds.maxY <= bounds.minY) return baseShape;
  const stopCount = 30;
  const stops = [];
  for (let i = 0; i <= stopCount; i += 1) {
    const t = i / stopCount;
    const x = bounds.minX + (bounds.maxX - bounds.minX) * t;
    stops.push(`<stop offset="${fmt(t * 100)}%" stop-color="${utilColor(utilAt(stations, x))}"></stop>`);
  }
  return `<defs>
      <clipPath id="beamShapeClip">
        <polygon points="${pointString(state.points)}"></polygon>
      </clipPath>
      <linearGradient id="beamStressGradient" gradientUnits="userSpaceOnUse" x1="${fmt(bounds.minX)}" y1="0" x2="${fmt(bounds.maxX)}" y2="0">
        ${stops.join("")}
      </linearGradient>
    </defs>
    <rect class="shape-fill" x="${fmt(bounds.minX)}" y="${fmt(bounds.minY)}" width="${fmt(bounds.maxX - bounds.minX)}" height="${fmt(bounds.maxY - bounds.minY)}" fill="url(#beamStressGradient)" clip-path="url(#beamShapeClip)"></rect>
    <polyline class="shape-outline" points="${closedPointString(state.points)}"></polyline>`;
}

function renderMesh(active) {
  if (!state.showMesh || !active?.nodes) return "";
  const lines = active.nodes.map((node) => {
    const section = verticalSections(state.points, safeSectionX(node.x, polygonBounds(state.points)));
    return section.intervals.map(([a, b]) => `<line class="mesh-line" x1="${fmt(node.x)}" y1="${fmt(a)}" x2="${fmt(node.x)}" y2="${fmt(b)}"></line>`).join("");
  });
  return `<g>${lines.join("")}</g>`;
}

function renderNeutralLine(active) {
  const bounds = polygonBounds(state.points);
  const pts = [];
  const n = 80;
  for (let i = 0; i <= n; i += 1) {
    const x = bounds.minX + ((bounds.maxX - bounds.minX) * i) / n;
    const section = verticalSections(state.points, safeSectionX(x, bounds));
    pts.push(`${fmt(x)},${fmt(section.center)}`);
  }
  return `<polyline class="neutral-line" points="${pts.join(" ")}"></polyline>`;
}

function renderDeformedLine(active) {
  if (!state.showDeflection || !active || active.error || !active.stations?.length) return "";
  const bounds = polygonBounds(state.points);
  const maxDefl = active.maxDeflection || 1;
  const displayScale = Math.min(180, Math.max(8, (bounds.maxY - bounds.minY) * 0.8 / Math.max(maxDefl, 0.001)));
  const pts = active.stations.map((station) => {
    const y = station.yCenter + station.deflection * displayScale;
    return `${fmt(station.x)},${fmt(y)}`;
  });
  return `<polyline class="deformed-line" points="${pts.join(" ")}"></polyline>`;
}

function renderDrawDraft() {
  if (!state.drawPoints.length) return "";
  const line = state.drawPoints.length > 1
    ? `<polyline class="shape-outline" points="${pointString(state.drawPoints)}"></polyline>`
    : "";
  const points = state.drawPoints.map(([x, y]) => `<circle class="draw-point" cx="${fmt(x)}" cy="${fmt(y)}" r="2.3"></circle>`).join("");
  return `<g>${line}${points}</g>`;
}

function renderVertices() {
  if (state.tool !== "edit") return "";
  return state.points.map(([x, y], index) => (
    `<circle class="vertex" data-vertex="${index}" cx="${fmt(x)}" cy="${fmt(y)}" r="2.8"></circle>`
  )).join("");
}

function renderSupports() {
  const bounds = polygonBounds(state.points);
  return state.supports.map((support) => {
    const x = clamp(support.x, bounds.minX, bounds.maxX);
    const sec = verticalSections(state.points, safeSectionX(x, bounds));
    const y = sec.maxY + 8;
    if (support.type === "fixed") {
      return `<g>
        <rect class="support-symbol" x="${fmt(x - 2)}" y="${fmt(sec.minY - 4)}" width="4" height="${fmt(sec.total + 12)}"></rect>
        <text class="support-label" x="${fmt(x + 4)}" y="${fmt(y)}">fixed</text>
      </g>`;
    }
    const path = support.type === "roller"
      ? `<circle class="support-symbol" cx="${fmt(x - 3)}" cy="${fmt(y + 3)}" r="1.4"></circle><circle class="support-symbol" cx="${fmt(x + 3)}" cy="${fmt(y + 3)}" r="1.4"></circle>`
      : "";
    return `<g>
      <polygon class="support-symbol" points="${fmt(x)},${fmt(sec.maxY + 1)} ${fmt(x - 5)},${fmt(y)} ${fmt(x + 5)},${fmt(y)}"></polygon>
      ${path}
      <text class="support-label" x="${fmt(x - 6)}" y="${fmt(y + 8)}">${support.type}</text>
    </g>`;
  }).join("");
}

function renderLoads() {
  const bounds = polygonBounds(state.points);
  return state.loads.map((load) => {
    if (load.type === "point") {
      const x = clamp(load.x, bounds.minX, bounds.maxX);
      const sec = verticalSections(state.points, safeSectionX(x, bounds));
      const top = sec.minY - 22;
      return `<g>
        <line class="load-arrow" x1="${fmt(x)}" y1="${fmt(top)}" x2="${fmt(x)}" y2="${fmt(sec.minY - 2)}"></line>
        <text class="load-label" x="${fmt(x + 3)}" y="${fmt(top + 5)}">${fmt(load.force)} N</text>
      </g>`;
    }
    const x1 = clamp(Math.min(load.x1, load.x2), bounds.minX, bounds.maxX);
    const x2 = clamp(Math.max(load.x1, load.x2), bounds.minX, bounds.maxX);
    const s1 = verticalSections(state.points, safeSectionX(x1, bounds));
    const s2 = verticalSections(state.points, safeSectionX(x2, bounds));
    const y = Math.min(s1.minY, s2.minY) - 20;
    const arrows = [];
    const count = Math.max(2, Math.min(8, Math.round((x2 - x1) / 18)));
    for (let i = 0; i <= count; i += 1) {
      const x = x1 + ((x2 - x1) * i) / count;
      const sec = verticalSections(state.points, safeSectionX(x, bounds));
      arrows.push(`<line class="load-arrow" x1="${fmt(x)}" y1="${fmt(y)}" x2="${fmt(x)}" y2="${fmt(sec.minY - 2)}"></line>`);
    }
    return `<g>
      <rect class="udl-band" x="${fmt(x1)}" y="${fmt(y - 5)}" width="${fmt(x2 - x1)}" height="5"></rect>
      ${arrows.join("")}
      <text class="load-label" x="${fmt(x1)}" y="${fmt(y - 7)}">${fmt(load.w)} N/mm</text>
    </g>`;
  }).join("");
}

function renderSectionProbe() {
  const bounds = polygonBounds(state.points);
  const y = sectionY(bounds);
  return `<line class="section-probe" x1="${fmt(bounds.minX - 30)}" y1="${fmt(y)}" x2="${fmt(bounds.maxX + 30)}" y2="${fmt(y)}"></line>`;
}

function renderAxes(bounds) {
  const width = Math.max(bounds.maxX - bounds.minX, 1);
  const height = Math.max(bounds.maxY - bounds.minY, 1);
  const len = Math.max(10, Math.min(width, height) * 0.14);
  const ox = bounds.minX + width * 0.07;
  const oy = bounds.maxY - height * 0.09;
  return `<g class="axis-triad" aria-label="Model axes: X horizontal, Z vertical">
    <circle class="axis-origin-dot" cx="${fmt(ox)}" cy="${fmt(oy)}" r="${fmt(len * 0.06)}"></circle>
    <line class="axis-arrow" x1="${fmt(ox)}" y1="${fmt(oy)}" x2="${fmt(ox + len)}" y2="${fmt(oy)}"></line>
    <line class="axis-arrow" x1="${fmt(ox)}" y1="${fmt(oy)}" x2="${fmt(ox)}" y2="${fmt(oy - len)}"></line>
    <text class="axis-label-strong" x="${fmt(ox + len + width * 0.012)}" y="${fmt(oy + height * 0.014)}">X</text>
    <text class="axis-label-strong" x="${fmt(ox - width * 0.006)}" y="${fmt(oy - len - height * 0.014)}">Z</text>
    <text class="axis-label" x="${fmt(ox)}" y="${fmt(oy + height * 0.055)}">mm grid</text>
  </g>`;
}

function renderResults() {
  const active = activeResult();
  if (!active || active.error) {
    els.metricList.innerHTML = `<dt>Status</dt><dd>${escapeHtml(active?.error || "No result")}</dd>`;
    els.riskBands.innerHTML = "";
    return;
  }
  els.metricList.innerHTML = [
    ["Max deflection", `${fmt(active.maxDeflection)} mm`],
    ["Max stress", `${fmt(active.maxStress)} MPa`],
    ["Allowable", `${fmt(active.allowable)} MPa`],
    ["Utilization", `${fmt(active.maxUtil)}x`],
    ["Max moment", `${fmt(active.maxMoment)} N mm`],
    ["Effective E", `${fmt(active.e)} MPa`],
  ].map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");

  els.riskBands.innerHTML = Object.entries(state.results || {}).map(([key, result]) => {
    if (result.error) {
      return `<div class="risk-row fail"><span>${scenarios[key].label}</span><div class="risk-track"><span style="width:100%"></span></div><strong>err</strong></div>`;
    }
    const level = result.maxUtil >= 1 ? "fail" : result.maxUtil >= 0.65 ? "watch" : "safe";
    return `<div class="risk-row ${level}">
      <span>${scenarios[key].label}</span>
      <div class="risk-track"><span style="width:${fmt(clamp(result.maxUtil, 0.02, 1.4) / 1.4 * 100)}%"></span></div>
      <strong>${fmt(result.maxUtil)}x</strong>
    </div>`;
  }).join("");
}

function renderDiagrams() {
  const active = activeResult();
  if (!active || active.error) {
    for (const svg of [els.deflectionDiagram, els.stressDiagram, els.momentDiagram, els.shearDiagram]) {
      svg.innerHTML = emptyDiagram("Check model");
    }
    return;
  }
  const stations = active.stations;
  els.deflectionPeak.textContent = `${fmt(active.maxDeflection)} mm`;
  els.stressPeak.textContent = `${fmt(active.maxStress)} MPa`;
  els.momentPeak.textContent = `${fmt(active.maxMoment)} N mm`;
  els.shearPeak.textContent = `${fmt(active.maxShear)} N`;
  drawDiagram(els.deflectionDiagram, stations, (s) => s.deflection, varColor("--accent-2"));
  drawDiagram(els.stressDiagram, stations, (s) => s.util, varColor("--red"), 1);
  drawDiagram(els.momentDiagram, stations, (s) => s.moment, varColor("--blue"));
  drawDiagram(els.shearDiagram, stations, (s) => s.shear, varColor("--violet"));
}

function drawDiagram(svg, stations, valueFn, color, threshold = null) {
  const width = 300;
  const height = 150;
  const pad = 18;
  const xs = stations.map((s) => s.x);
  const values = stations.map(valueFn);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const maxAbs = Math.max(0.001, ...values.map((v) => Math.abs(v)));
  const xScale = (x) => pad + ((x - minX) / Math.max(1, maxX - minX)) * (width - pad * 2);
  const yScale = (v) => height / 2 - (v / maxAbs) * (height / 2 - pad);
  const points = stations.map((s, i) => `${fmt(xScale(s.x))},${fmt(yScale(values[i]))}`).join(" ");
  const area = `${fmt(xScale(minX))},${height / 2} ${points} ${fmt(xScale(maxX))},${height / 2}`;
  const thresholdLine = threshold === null ? "" : `<line class="diagram-axis" x1="${pad}" y1="${fmt(yScale(threshold))}" x2="${width - pad}" y2="${fmt(yScale(threshold))}"></line>`;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = `<polygon class="diagram-area" fill="${color}" points="${area}"></polygon>
    <line class="diagram-axis" x1="${pad}" y1="${height / 2}" x2="${width - pad}" y2="${height / 2}"></line>
    ${thresholdLine}
    <polyline class="diagram-line" stroke="${color}" points="${points}"></polyline>`;
}

function emptyDiagram(message) {
  return `<svg viewBox="0 0 300 150"><text x="18" y="76" fill="currentColor">${escapeHtml(message)}</text></svg>`;
}

function renderSectionView() {
  const bounds = polygonBounds(state.points);
  const y = sectionY(bounds);
  const sec = horizontalSections(state.points, safeSectionY(y, bounds));
  const occupiedLength = Math.max(0.2, sec.total);
  const thickness = Math.max(0.2, state.thickness);
  const layerHeight = positiveNumber(els.layerHeight.value, 0.2);
  const lineWidth = positiveNumber(els.lineWidth.value, 0.45);
  const perimeters = Math.max(1, Math.round(positiveNumber(els.perimeters.value, 3)));
  const viewW = 210;
  const viewH = 190;
  const span = Math.max(1, bounds.maxX - bounds.minX);
  const baseScale = Math.min(170 / span, 94 / Math.max(thickness, 1));
  const scale = baseScale * state.sliceZoom;
  const xOrigin = viewW / 2 - (span * scale) / 2 - state.slicePanX * scale;
  const yOrigin = viewH / 2 - (thickness * scale) / 2 - state.slicePanY * scale;
  const sliceRows = [];
  const wallLines = [];
  const infill = [];
  const layerIndex = Math.max(0, Math.round((y - bounds.minY) / layerHeight));
  const layerSnapY = bounds.minY + layerIndex * layerHeight;

  sec.intervals.forEach(([a, b], index) => {
    const x0 = xOrigin + (a - bounds.minX) * scale;
    const y0 = yOrigin;
    const w = Math.max(1, (b - a) * scale);
    const h = Math.max(1, thickness * scale);
    const clipId = `sectionClip${index}`;
    sliceRows.push(`<clipPath id="${clipId}"><rect x="${fmt(x0)}" y="${fmt(y0)}" width="${fmt(w)}" height="${fmt(h)}" rx="3"></rect></clipPath>`);
    sliceRows.push(`<rect class="section-solid" x="${fmt(x0)}" y="${fmt(y0)}" width="${fmt(w)}" height="${fmt(h)}" rx="3"></rect>`);
    const wallInset = Math.min(w / 2 - 1, Math.max(1, lineWidth * scale));
    for (let i = 1; i <= perimeters; i += 1) {
      const inset = Math.min(w / 2 - 1, wallInset * i);
      wallLines.push(`<rect class="wall-line" x="${fmt(x0 + inset)}" y="${fmt(y0 + inset)}" width="${fmt(Math.max(1, w - inset * 2))}" height="${fmt(Math.max(1, h - inset * 2))}" fill="none"></rect>`);
    }
    const spacing = Math.max(8, lineWidth * scale * 5);
    for (let dx = -h; dx < w + h; dx += spacing) {
      infill.push(`<line class="infill-line" clip-path="url(#${clipId})" x1="${fmt(x0 + dx)}" y1="${fmt(y0 + h)}" x2="${fmt(x0 + dx + h)}" y2="${fmt(y0)}"></line>`);
    }
  });

  const layerLines = [];
  const layerBandY = viewH - 26;
  layerLines.push(`<line class="layer-line selected-layer" x1="22" y1="${fmt(layerBandY)}" x2="${fmt(viewW - 22)}" y2="${fmt(layerBandY)}"></line>`);
  els.sectionXLabel.textContent = `layer y = ${fmt(y - bounds.minY)} mm`;
  els.sectionView.innerHTML = `<svg viewBox="0 0 ${viewW} ${viewH}" aria-label="Horizontal sliced layer">
    <defs>${sliceRows.filter((row) => row.startsWith("<clipPath")).join("")}</defs>
    ${sliceRows.filter((row) => !row.startsWith("<clipPath")).join("")}
    ${infill.join("")}
    ${wallLines.join("")}
    ${layerLines.join("")}
    <text class="section-label" x="${fmt(viewW / 2)}" y="18" text-anchor="middle">horizontal layer ${layerIndex} at y=${fmt(layerSnapY - bounds.minY)} mm</text>
    <text class="section-label" x="${fmt(viewW / 2)}" y="${fmt(viewH - 10)}" text-anchor="middle">${fmt(occupiedLength)} mm occupied span / ${fmt(thickness)} mm part thickness / ${fmt(state.sliceZoom)}x</text>
  </svg>`;
}

function renderItems() {
  const supportRows = state.supports.map((support) => `<div class="item-row">
    <div><strong>${escapeHtml(capitalize(support.type))} support</strong><span>x = ${fmt(support.x)} mm</span></div>
    <button class="item-action" type="button" data-delete="support:${escapeAttr(support.id)}"><i data-lucide="trash-2"></i></button>
  </div>`);
  const loadRows = state.loads.map((load) => {
    const label = load.type === "point"
      ? `Point load ${fmt(load.force)} N`
      : `UDL ${fmt(load.w)} N/mm`;
    const meta = load.type === "point"
      ? `x = ${fmt(load.x)} mm`
      : `${fmt(Math.min(load.x1, load.x2))}-${fmt(Math.max(load.x1, load.x2))} mm`;
    return `<div class="item-row">
      <div><strong>${escapeHtml(label)}</strong><span>${escapeHtml(meta)}</span></div>
      <button class="item-action" type="button" data-delete="load:${escapeAttr(load.id)}"><i data-lucide="trash-2"></i></button>
    </div>`;
  });
  const rows = [...supportRows, ...loadRows];
  els.itemCount.textContent = `${rows.length} item${rows.length === 1 ? "" : "s"}`;
  els.itemList.innerHTML = rows.join("") || `<p>No supports or loads defined.</p>`;
}

function renderLoadList() {
  els.loadCount.textContent = String(state.loads.length);
  els.loadList.innerHTML = state.loads.map((load) => {
    const label = load.type === "point"
      ? `Point ${fmt(load.force)} N`
      : `UDL ${fmt(load.w)} N/mm`;
    const meta = load.type === "point"
      ? `x = ${fmt(load.x)} mm`
      : `${fmt(Math.min(load.x1, load.x2))}-${fmt(Math.max(load.x1, load.x2))} mm`;
    return `<div class="inline-item">
      <div><strong>${escapeHtml(label)}</strong><span>${escapeHtml(meta)}</span></div>
      <button class="item-action" type="button" data-delete="load:${escapeAttr(load.id)}" aria-label="Delete ${escapeAttr(label)}"><i data-lucide="trash-2"></i></button>
    </div>`;
  }).join("") || `<p>No applied loads.</p>`;
}

function onSvgPointerDown(event) {
  const vertex = event.target.closest?.("[data-vertex]");
  if (state.tool === "pan") {
    state.panning = {
      startX: event.clientX,
      startY: event.clientY,
      panX: state.panX,
      panY: state.panY,
      viewBox: [...state.lastViewBox],
    };
    els.modelSvg.setPointerCapture?.(event.pointerId);
    return;
  }
  const point = snapSvgEvent(event);
  if (state.tool === "edit" && vertex) {
    state.draggingVertex = Number(vertex.dataset.vertex);
    els.modelSvg.setPointerCapture?.(event.pointerId);
    return;
  }
  if (state.tool === "draw") {
    state.drawPoints.push([point.x, point.y]);
    renderAll();
    return;
  }
  if (state.tool === "support") {
    addSupport(point.x, els.supportType.value);
    solveAndRender("Support placed");
    return;
  }
  if (state.tool === "pointLoad") {
    addPointLoad(point.x, Number(els.pointForce.value));
    solveAndRender("Point load placed");
    return;
  }
  if (state.tool === "udl") {
    if (state.pendingUdlStart === null) {
      state.pendingUdlStart = point.x;
      toast("UDL start set. Click the end position.");
    } else {
      addUdl(state.pendingUdlStart, point.x, Number(els.udlMag.value));
      state.pendingUdlStart = null;
      solveAndRender("UDL placed");
    }
  }
}

function onSvgPointerMove(event) {
  if (state.panning) {
    const [, , width, height] = state.panning.viewBox;
    const rect = els.modelSvg.getBoundingClientRect();
    const dx = ((event.clientX - state.panning.startX) / Math.max(1, rect.width)) * width;
    const dy = ((event.clientY - state.panning.startY) / Math.max(1, rect.height)) * height;
    state.panX = state.panning.panX - dx;
    state.panY = state.panning.panY - dy;
    renderAll();
    return;
  }
  if (state.draggingVertex === null) return;
  const point = snapSvgEvent(event);
  state.points[state.draggingVertex] = [point.x, point.y];
  state.points = normalizePolygon(state.points);
  solveAndRender("Geometry edited");
}

function onSvgPointerUp() {
  state.draggingVertex = null;
  state.panning = null;
}

function addSupport(x, type) {
  const bounds = polygonBounds(state.points);
  state.supports.push({
    id: uniqueId("s"),
    type: ["fixed", "pinned", "roller"].includes(type) ? type : "roller",
    x: clamp(snapScalar(Number(x)), bounds.minX, bounds.maxX),
  });
}

function addPointLoad(x, force) {
  const bounds = polygonBounds(state.points);
  state.loads.push({
    id: uniqueId("p"),
    type: "point",
    x: clamp(snapScalar(Number(x)), bounds.minX, bounds.maxX),
    force: Number.isFinite(force) ? force : 50,
  });
}

function addUdl(x1, x2, w) {
  const bounds = polygonBounds(state.points);
  const a = clamp(snapScalar(Number(x1)), bounds.minX, bounds.maxX);
  const b = clamp(snapScalar(Number(x2)), bounds.minX, bounds.maxX);
  if (Math.abs(a - b) < state.grid) {
    toast("UDL needs a nonzero interval.");
    return;
  }
  state.loads.push({
    id: uniqueId("u"),
    type: "udl",
    x1: a,
    x2: b,
    w: Number.isFinite(w) ? w : 0.2,
  });
}

function fitSupportsAndLoadsToGeometry() {
  const bounds = polygonBounds(state.points);
  state.supports = state.supports.map((support) => ({ ...support, x: clamp(support.x, bounds.minX, bounds.maxX) }));
  state.loads = state.loads.map((load) => load.type === "point"
    ? { ...load, x: clamp(load.x, bounds.minX, bounds.maxX) }
    : { ...load, x1: clamp(load.x1, bounds.minX, bounds.maxX), x2: clamp(load.x2, bounds.minX, bounds.maxX) });
}

function activeResult() {
  return state.results?.[state.activeScenario] || null;
}

function summarizeResultsForTest() {
  const active = activeResult();
  return active ? {
    error: active.error || null,
    maxDeflection: active.maxDeflection || 0,
    maxStress: active.maxStress || 0,
    maxUtil: active.maxUtil || 0,
    supportCount: state.supports.length,
    loadCount: state.loads.length,
  } : null;
}

function verticalSections(points, x) {
  const hits = [];
  for (let i = 0; i < points.length; i += 1) {
    const [x1, y1] = points[i];
    const [x2, y2] = points[(i + 1) % points.length];
    if (Math.abs(x2 - x1) < 1e-9) continue;
    const minX = Math.min(x1, x2);
    const maxX = Math.max(x1, x2);
    if (x < minX || x >= maxX) continue;
    const t = (x - x1) / (x2 - x1);
    hits.push(y1 + t * (y2 - y1));
  }
  const ys = hits.sort((a, b) => a - b);
  const intervals = [];
  for (let i = 0; i < ys.length - 1; i += 2) {
    intervals.push([ys[i], ys[i + 1]]);
  }
  const total = intervals.reduce((sum, [a, b]) => sum + Math.max(0, b - a), 0);
  const minY = intervals.length ? Math.min(...intervals.map(([a]) => a)) : 0;
  const maxY = intervals.length ? Math.max(...intervals.map(([, b]) => b)) : minY;
  const weightedCenter = intervals.reduce((sum, [a, b]) => sum + ((a + b) / 2) * Math.max(0, b - a), 0);
  return {
    intervals,
    total,
    minY,
    maxY,
    center: total > 0 ? weightedCenter / total : (minY + maxY) / 2,
  };
}

function horizontalSections(points, y) {
  const hits = [];
  for (let i = 0; i < points.length; i += 1) {
    const [x1, y1] = points[i];
    const [x2, y2] = points[(i + 1) % points.length];
    if (Math.abs(y2 - y1) < 1e-9) continue;
    const minY = Math.min(y1, y2);
    const maxY = Math.max(y1, y2);
    if (y < minY || y >= maxY) continue;
    const t = (y - y1) / (y2 - y1);
    hits.push(x1 + t * (x2 - x1));
  }
  const xs = hits.sort((a, b) => a - b);
  const intervals = [];
  for (let i = 0; i < xs.length - 1; i += 2) {
    intervals.push([xs[i], xs[i + 1]]);
  }
  const total = intervals.reduce((sum, [a, b]) => sum + Math.max(0, b - a), 0);
  return { intervals, total };
}

function safeSectionX(x, bounds) {
  return clamp(x, bounds.minX + 1e-5, bounds.maxX - 1e-5);
}

function sectionX(bounds) {
  return safeSectionX(bounds.minX + ((bounds.maxX - bounds.minX) * state.sectionPct) / 100, bounds);
}

function safeSectionY(y, bounds) {
  return clamp(y, bounds.minY + 1e-5, bounds.maxY - 1e-5);
}

function sectionY(bounds) {
  return safeSectionY(bounds.minY + ((bounds.maxY - bounds.minY) * state.sectionPct) / 100, bounds);
}

function nearestNode(nodes, x) {
  let best = 0;
  let bestDist = Infinity;
  for (let i = 0; i < nodes.length; i += 1) {
    const dist = Math.abs(nodes[i].x - x);
    if (dist < bestDist) {
      best = i;
      bestDist = dist;
    }
  }
  return best;
}

function polygonBounds(points) {
  return {
    minX: Math.min(...points.map(([x]) => x)),
    maxX: Math.max(...points.map(([x]) => x)),
    minY: Math.min(...points.map(([, y]) => y)),
    maxY: Math.max(...points.map(([, y]) => y)),
  };
}

function paddedBounds(points, zoom) {
  const b = polygonBounds(points);
  const width = Math.max(80, b.maxX - b.minX);
  const height = Math.max(50, b.maxY - b.minY);
  const padX = 34;
  const padY = 44;
  const centerX = (b.minX + b.maxX) / 2;
  const centerY = (b.minY + b.maxY) / 2;
  const viewW = (width + padX * 2) / zoom;
  const viewH = (height + padY * 2) / zoom;
  return {
    minX: centerX - viewW / 2,
    maxX: centerX + viewW / 2,
    minY: centerY - viewH / 2,
    maxY: centerY + viewH / 2,
  };
}

function normalizePolygon(points) {
  if (points.length < 3) return points;
  const area = signedArea(points);
  return area < 0 ? [...points].reverse() : points;
}

function signedArea(points) {
  let area = 0;
  for (let i = 0; i < points.length; i += 1) {
    const [x1, y1] = points[i];
    const [x2, y2] = points[(i + 1) % points.length];
    area += x1 * y2 - x2 * y1;
  }
  return area / 2;
}

function snapSvgEvent(event) {
  const point = els.modelSvg.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  const matrix = els.modelSvg.getScreenCTM();
  const transformed = matrix ? point.matrixTransform(matrix.inverse()) : point;
  const [x, y] = snapPoint(transformed.x, transformed.y);
  return { x, y };
}

function snapPoint(x, y) {
  return [snapScalar(x), snapScalar(y)];
}

function snapScalar(value) {
  const step = state.grid || 1;
  return Math.round(value / step) * step;
}

function utilAt(stations, x) {
  if (!stations.length) return 0;
  let best = stations[0];
  let bestDist = Math.abs(stations[0].x - x);
  for (const station of stations) {
    const dist = Math.abs(station.x - x);
    if (dist < bestDist) {
      best = station;
      bestDist = dist;
    }
  }
  return best.util;
}

function utilColor(util) {
  const value = clamp(util, 0, 1.35);
  if (value < 0.55) {
    return mixColor([121, 217, 157], [232, 196, 91], value / 0.55);
  }
  if (value < 1) {
    return mixColor([232, 196, 91], [240, 126, 121], (value - 0.55) / 0.45);
  }
  return mixColor([240, 126, 121], [185, 70, 84], (value - 1) / 0.35);
}

function mixColor(a, b, t) {
  const c = a.map((v, i) => Math.round(v + (b[i] - v) * clamp(t, 0, 1)));
  return `rgb(${c[0]} ${c[1]} ${c[2]})`;
}

function svgDefs() {
  return `<defs>
    <marker id="arrowHead" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="var(--red)"></path>
    </marker>
    <marker id="axisArrowHead" markerWidth="6" markerHeight="6" refX="5.2" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="var(--accent)"></path>
    </marker>
  </defs>`;
}

function pointString(points) {
  return points.map(([x, y]) => `${fmt(x)},${fmt(y)}`).join(" ");
}

function closedPointString(points) {
  return `${pointString(points)} ${fmt(points[0][0])},${fmt(points[0][1])}`;
}

function clonePoints(points) {
  return points.map(([x, y]) => [x, y]);
}

function positiveNumber(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

function uniqueId(prefix) {
  return `${prefix}${Math.random().toString(36).slice(2, 8)}`;
}

function toolHint(tool) {
  const hints = {
    edit: "Edit mode: drag vertices. Switch tools to place supports or loads.",
    draw: "Draw mode: click grid points around the shape, then close it.",
    support: "Support mode: click a span position to place the selected support type.",
    pointLoad: "Point-load mode: click the beam to place the current force.",
    udl: "UDL mode: click start, then click end to place the distributed load.",
    pan: "Pan mode: drag the canvas to move the view. Use Reset View to fit the part again.",
  };
  return hints[tool] || hints.edit;
}

function isMajor(value) {
  return Math.abs(value / 10 - Math.round(value / 10)) < 1e-6;
}

function capitalize(value) {
  const text = String(value || "");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function fmt(value) {
  if (!Number.isFinite(Number(value))) return "0";
  const n = Number(value);
  if (Math.abs(n) >= 10000) return n.toExponential(2);
  if (Math.abs(n) >= 1000) return n.toFixed(0);
  if (Math.abs(n) >= 100) return n.toFixed(1);
  if (Math.abs(n) >= 10) return n.toFixed(2);
  if (Math.abs(n) >= 1) return n.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  return n.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
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

function varColor(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function toast(message) {
  els.toast.textContent = message;
  els.toast.hidden = false;
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => {
    els.toast.hidden = true;
  }, 2200);
}

function refreshIcons() {
  if (window.lucide?.createIcons) {
    window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
  }
}
