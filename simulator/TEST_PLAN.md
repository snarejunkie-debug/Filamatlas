# FDM Beam Bounds - Test Plan and Run Log

Date: 2026-06-06

## Test Goals

- Verify the simulator produces correct first-order beam results for cases with known analytical answers.
- Verify datasheet scenario factors change stiffness, allowable stress, and utilization in predictable directions.
- Verify geometry-derived section properties update when the polygon changes.
- Verify supports, loads, and invalid model states are handled clearly.
- Verify the UI interactions a user needs for a complete workflow work end to end.
- Verify the app does not leave stale results after changes.
- Verify layout remains usable on desktop and mobile-like widths.

## Acceptance Criteria

- Default simply supported beam result is within 2% of the closed-form Euler-Bernoulli solution.
- UI edits recompute within 150 ms for normal preset models, excluding browser automation overhead.
- All primary controls visibly update state without console errors.
- Invalid models show a clear model error rather than blank or misleading values.
- Main desktop layout shows canvas, scenario metrics, slice view, and at least one row of diagrams without overlap.
- Mobile-width layout stacks controls and results without clipped labels or overlapping text.

## Functional Solver Tests

| ID | Test | Expected Result | Status |
| --- | --- | --- | --- |
| F-01 | Default beam, realistic scenario: compare max deflection against `P L^3 / (48 E I)` with `P=80 N`, `L=140 mm`, `E=2400 MPa`, `I=4000 mm^4`. | About `0.476 mm`, within 2%. | Pass |
| F-02 | Default beam, realistic scenario: compare max bending stress against `M c / I` with `M=P L/4=2800 N mm`, `c=10 mm`, `I=4000 mm^4`. | About `7.0 MPa`, within 2%. | Pass |
| F-03 | Default beam scenarios. | Deflection increases from optimistic to realistic to pessimistic. | Pass |
| F-04 | Default beam scenarios. | Utilization increases from optimistic to realistic to pessimistic. | Pass |
| F-05 | Print direction across span. | Effective E and allowable reduce versus roads-along-span. | Pass |
| F-06 | Material preset PETG. | E and strength inputs update to PETG values and results recompute. | Pass |
| F-07 | Custom material input. | Material preset switches to Custom and metrics recompute. | Pass |
| F-08 | Thickness increase. | Deflection and stress decrease versus baseline. | Pass |
| F-09 | Notched preset. | Max stress/utilization rises versus straight beam under comparable loading. | Pass |
| F-10 | Tapered cantilever preset. | Solver reports finite deflection/stress with one fixed support. | Pass |
| F-11 | Bracket preset. | Solver reports finite deflection/stress with one fixed support. | Pass |
| F-12 | Remove all supports. | Clear under-constrained model error appears. | Pass |
| F-13 | Add one roller only to a simply supported-style model. | Clear under-constrained model error appears. | Pass |
| F-14 | Zero/nonpositive UDL interval. | Load is rejected and item count does not increase. | Pass |
| F-15 | Section slider over straight beam. | Section local height remains constant. | Pass |
| F-16 | Section slider over notched beam. | Section local height drops in notch region. | Pass |
| F-17 | Draw closed rectangle. | Geometry closes, edit mode resumes, solver remains finite. | Pass |
| F-18 | Mesh toggle after solve. | Mesh lines appear and count is nonzero. | Pass |
| F-19 | Stress toggle off/on. | Stress overlay hides and returns without changing numerical result. | Pass |
| F-20 | Deflection toggle off/on. | Deformed line hides and returns without changing numerical result. | Pass |

## UI Interaction Tests

| ID | Test | Expected Result | Status |
| --- | --- | --- | --- |
| U-01 | Page load. | Title, default solved status, canvas, metrics, diagrams, and item list visible. | Pass |
| U-02 | Run Bounds button. | Status updates with solve timing and metrics remain finite. | Pass |
| U-03 | Preset buttons: Beam, Notched, Tapered, Bracket. | Active preset changes and result summary updates. | Pass |
| U-04 | Scenario segmented control. | Active scenario label and metrics update. | Pass |
| U-05 | Grid select: 0.5, 1, 10 mm. | Readout updates and geometry snaps without disappearing. | Pass |
| U-06 | Zoom controls. | SVG viewBox changes and handles remain usable. | Pass |
| U-07 | Vertex drag in edit mode. | Polygon points change and solve status updates. | Pass |
| U-08 | Support mode canvas click. | New support appears in canvas and model item list. | Pass |
| U-09 | Point load mode canvas click. | New load arrow appears in canvas and model item list. | Pass |
| U-10 | UDL mode two canvas clicks. | UDL band/arrows appear and model item list updates. | Pass |
| U-11 | Add Support button. | Support is added from input fields. | Pass |
| U-12 | Add Point Load button. | Point load is added from input fields. | Pass |
| U-13 | Add UDL button. | UDL is added from input fields. | Pass |
| U-14 | Delete support from item list. | Support row disappears and model recomputes. | Pass |
| U-15 | Delete load from item list. | Load row disappears and model recomputes. | Pass |
| U-16 | Draw mode with fewer than three points. | Close Shape remains disabled. | Pass |
| U-17 | Draw mode with four points and Close Shape. | Shape replaces geometry and tool returns to Edit. | Pass |
| U-18 | Reset Draw. | Draft points disappear without replacing geometry. | Pass |
| U-19 | Slice controls: section, layer height, line width, walls. | Slice preview updates; wall count follows wall input. | Pass |
| U-20 | View toggles: Stress, Deflection, Mesh. | Associated overlay appears/disappears. | Pass |
| U-21 | Desktop layout at current desktop viewport. | Canvas, scenario metrics, slice view, and diagrams visible without overlap. | Pass |
| U-22 | Mobile-like layout at 390 px harness width. | Panels stack and controls remain readable. | Pass |
| U-23 | Console check after interaction pass. | No browser console errors or warnings. | Pass |

## Run Results

Run summary: 43 tests passed, 0 failed.

Functional evidence highlights:

- F-01: default deflection `0.4763 mm`; closed-form expected `0.476389 mm`.
- F-02: default max stress `6.999 MPa`; closed-form expected `7.0 MPa`.
- F-03: deflection ordered correctly: optimistic `0.3572 mm`, realistic `0.4763 mm`, pessimistic `0.6495 mm`.
- F-04: utilization ordered correctly: optimistic `0.1609x`, realistic `0.2682x`, pessimistic `0.4827x`.
- F-05: roads-across-span derated effective E from `2400 MPa` to `1680 MPa` and allowable from `26.10 MPa` to `18.27 MPa`.
- F-09: notched beam stress rose from `6.999 MPa` to `37.19 MPa`; utilization rose from `0.2682x` to `1.425x`.
- F-12/F-13: unsupported and under-constrained models both produced clear status messages.
- F-16: notched section view changed from `24.00 mm local height` outside the notch to `14.00 mm local height` inside it.

UI evidence highlights:

- U-01: default load showed `Initial solve` status, four diagrams, and three model items.
- U-03: all four presets activated and produced finite metrics.
- U-06: explicit zoom buttons changed SVG viewBox from `-34.00 -59.00 208.0 138.0` to `-10.00 -43.08 160.0 106.2`.
- U-07: vertex drag changed the polygon outline and produced `Geometry edited` solve status.
- U-08/U-09/U-10: canvas placement added support, point load, and UDL items.
- U-14/U-15: item delete buttons removed supports and loads and recomputed.
- U-19: slice controls updated layer/line/wall values; wall line count matched `4`.
- U-21: desktop layout at `1280 x 720` had no canvas overlap with results or diagrams.
- U-22: `responsive-harness.html` verified the app inside a `390 x 820` mobile-width frame.
- U-23: browser console contained `0` errors/warnings after the pass.

Issues found and fixed during this run:

- Native range zoom was brittle under browser automation, so explicit zoom in/out buttons were added while keeping the slider.
- Browser cache served old JS after the zoom-button change, so simulator CSS/JS asset URLs were versioned.
- The canvas SVG could overflow its grid row and overlap diagrams; CSS was adjusted so the canvas respects its grid track.
- A same-origin `responsive-harness.html` was added for repeatable mobile-width layout checks.

Artifacts:

- Desktop QA screenshot: `analysis/fdm-simulator-qa-desktop.png`
- Mobile-width harness screenshot: `analysis/fdm-simulator-qa-mobile-harness.png`

## Regression Run - Slice Direction and Navigation

Date: 2026-06-07

Additional fixes:

- Horizontal slicing now uses a `y` layer through the 2D side profile instead of a vertical `x` section station.
- The model canvas shows the active slice as a horizontal probe line.
- Loads now have a dedicated `Applied Loads` list in the Loads panel with visible delete buttons.
- Main view navigation now includes zoom in/out, pan buttons, reset view, and a Pan tool for drag-panning.
- Slice view navigation now includes layer up/down, zoom in/out, pan up/down/left/right, and reset.
- The deflection overlay control is labeled `Deflected Shape`.

Regression checks:

| ID | Test | Result |
| --- | --- | --- |
| R-01 | Initial slice probe is horizontal, with `y1 == y2`. | Pass |
| R-02 | Layer Up moves the slice label and horizontal probe from `10.00 mm` to `10.40 mm`. | Pass |
| R-03 | Slice zoom and pan controls change the slice SVG and report updated zoom text. | Pass |
| R-04 | Applied load delete button removes the load from the canvas and both model lists. | Pass |
| R-05 | Main zoom and pan buttons change the model SVG `viewBox`. | Pass |
| R-06 | Pan tool drag changes the model SVG `viewBox`. | Pass |
| R-07 | Deflected Shape toggle hides and restores the `.deformed-line` overlay. | Pass |
| R-08 | Browser console after regression checks. | Pass, 0 errors/warnings |
| R-09 | Main model view shows explicit X and Z direction indicators. | Pass |
| R-10 | Default stress overlay renders as one opaque clipped gradient fill, not vertical strip polygons. | Pass |
| R-11 | Mesh visualization is off by default, with `0` `.mesh-line` elements rendered. | Pass |
| R-12 | Browser console after axis/stress-fill regression checks. | Pass, 0 errors |

Regression artifact:

- Screenshot: `analysis/fdm-simulator-slice-pan-regression.png`
- Screenshot: `analysis/fdm-simulator-axis-gradient-regression.png`
