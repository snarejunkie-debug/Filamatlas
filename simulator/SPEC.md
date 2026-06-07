# FDM Beam Bounds - Tool Spec

## Purpose

FDM Beam Bounds is a lightweight browser tool for early design screening of printed beam-like parts. It should let a user sketch a 2D side profile, define supports and loads, inspect deflection and stress risk, and compare optimistic/realistic/pessimistic material scenarios derived from limited datasheet inputs.

This is not a certification-grade FEA tool. It is a fast bounding and intuition tool that should make weak geometry, poor slenderness, and print-risk assumptions visible before the user spends time in a slicer or a full CAD/FEA workflow.

## Research Notes

- EduBeam emphasizes immediate feedback: edit span, supports, or loads and diagrams recompute in-browser. Its GitHub README calls out Timoshenko beams, truss elements, real-time reactions/displacements/internal-force visualization, and shareable JSON/URLs. Source: https://www.edubeam.app/ and https://github.com/janvorisek/edubeam
- MechSimulator's beam tool shows the core UX pattern for this class of app: beam diagram, SFD, BMD, deflection, drag-and-drop point loads, UDLs, moment loads, toggles, and undo. Source: https://mechsimulator.com/tools/beam-bending/
- FEAScript shows that browser-side finite element work is viable and should be structured as portable JavaScript with interactive visualization/post-processing. Source: https://feascript.com/index.html
- CalcSteel and Stabileo suggest that serious browser solvers make the model inspectable: nodes, supports, loads, result overlays, and code/check outputs are visible rather than hidden behind a single "solve" button. Sources: https://calcsteel.com/about and https://stabileo.com/

## MVP Scope

### Included

- Standalone web app separate from the Filament Material Atlas.
- Editable 2D side-profile polygon on a millimeter grid.
- Grid snap with selectable spacing: 0.5, 1, 2, 5, 10 mm.
- Zoom control.
- Presets for straight beam, notched beam, tapered beam, and bracket-like geometry.
- Vertex dragging in edit mode.
- Polygon drawing mode with close/reset actions.
- Support definition:
  - Fixed support constrains displacement and rotation.
  - Pinned and roller supports constrain vertical displacement in the beam model.
- Load definition:
  - Point loads in newtons.
  - Uniform distributed loads in N/mm over an interval.
- Auto-solve plus explicit Run Bounds button.
- Optimistic, realistic, and pessimistic scenarios from datasheet modulus and strength knockdowns.
- Deformed-shape overlay.
- Stress/utilization color overlay on the side profile.
- Diagrams for deflection, bending moment, shear, and stress/utilization.
- Sliding section/slice view tied to x-position.
- Section view includes:
  - local height from polygon intersection,
  - out-of-plane thickness,
  - layer-height bands,
  - perimeter/infill indication,
  - width/span readout.
- Result summary:
  - max deflection,
  - max bending stress,
  - max utilization,
  - max moment,
  - governing scenario,
  - model stability/error state.

### Excluded From MVP

- Full 2D plane-stress meshing.
- Contact, plasticity, nonlinear deflection, buckling, fatigue, creep, or thermal warping.
- True notch-root stress concentration from local mesh refinement.
- Real slicer G-code generation.
- Automatic import from STL/DXF/SVG.

## Solver Model

The MVP uses a 1D Euler-Bernoulli beam finite element solver with variable section properties sampled from the 2D polygon:

- Units: mm, N, MPa.
- Element stiffness uses local `EI`, where `I = thickness * localHeight^3 / 12`.
- Area uses `A = thickness * localHeight`.
- Deflection is vertical displacement along the span.
- Bending stress uses `sigma = M * c / I`.
- Rectangular shear estimate uses `tau = 1.5 * V / A`.
- Utilization uses `max(sigma, tau) / allowable`.
- Stress concentration is a labeled heuristic multiplier near abrupt local-height changes, not a resolved notch stress.

## Datasheet Scenario Defaults

The user enters datasheet modulus `E` and tensile/flexural strength.

- Optimistic:
  - `E = 1.00 * datasheetE`
  - `allowable = 0.75 * datasheetStrength`
- Realistic:
  - `E = 0.75 * datasheetE`
  - `allowable = 0.45 * datasheetStrength`
- Pessimistic:
  - `E = 0.55 * datasheetE`
  - `allowable = 0.25 * datasheetStrength`

Print direction modifies the effective modulus and allowable:

- Along span: no additional penalty.
- Across span: `E *= 0.70`, `allowable *= 0.70`.
- Unknown/mixed: `E *= 0.85`, `allowable *= 0.80`.

## UX Metrics

- A first-time user can create a simple supported beam with one point load and see deflection/stress in under 60 seconds.
- Every model edit visibly recomputes results within 150 ms for the default mesh.
- No result panel should display stale results after geometry, material, support, or load changes.
- The default model must be stable and solved on page load.
- All primary interactions must work with mouse:
  - preset switch,
  - mode switch,
  - vertex drag,
  - support click-add,
  - point-load click-add,
  - UDL two-click add,
  - section slider,
  - grid select,
  - zoom slider,
  - scenario switch,
  - delete support/load,
  - Run Bounds.
- At 1366 x 768, the main canvas, right result summary, and at least one row of diagrams must be visible without layout overlap.
- At 390 px width, controls stack cleanly and no text overlaps control boundaries.

## Test Plan

- Load app and confirm the default model solves.
- Switch each preset and confirm solver result remains finite or reports a clear stability error.
- Change grid from 1 mm to 0.5 mm and 10 mm.
- Drag a vertex and confirm geometry points and results change.
- Add a support by canvas click in support mode.
- Add a point load by canvas click in point-load mode.
- Add a UDL by two canvas clicks in UDL mode.
- Delete one support and one load from the model list.
- Change material preset and custom strength/modulus inputs.
- Change scenario tab and confirm metrics update.
- Move section slider and confirm section height/slice graphic updates.
- Change zoom and confirm SVG viewBox updates without losing handles.
- Use Draw mode to create and close a valid polygon.
- Check browser console for errors and warnings.
