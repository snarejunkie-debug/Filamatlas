# Filament Material Atlas Project Spec

## Product Definition

Filament Material Atlas is a source-backed 3D printing filament material database and comparison tool. It is intended for makers, engineers, and materials-curious users who need to compare FFF/FDM filament properties without reading dozens of vendor datasheets by hand.

The atlas must make materials easy to browse visually while preserving engineering traceability. Every published numeric value must be tied to a source document or source row, be plausible for its property, and be safe to use in comparison tables, charts, and material-detail summaries.

## Data Quality Policy

Published data must be conservative. If a numeric value cannot be confidently aligned to a datasheet property/value row, it must be omitted from the published JSON, SQLite, CSV, and UI charts.

Rejected or suspicious candidates must not disappear silently. They must be recorded in an audit artifact with enough context to improve the parser later:

- supplier, product, source file, and source type
- property key and label
- rejected raw value
- reason for rejection
- source context

Known rejection classes include:

- unit exponents captured as values, such as `g/cm³`, `cm³`, `mm³`, `m²`, `kJ/m²`, or broken extracted text like `g/cm | 3`
- footnote markers such as `(1)`, `(2)`, or standalone `1`, `2`, `3` after unit labels
- method codes such as ISO/ASTM/GB/T identifiers
- table headers such as Unit, Typical Value, Method, or Testing Method
- values from neighboring properties, such as bed temperature captured as nozzle temperature
- unrelated commercial fields, such as filament length captured as impact strength

## Source Traceability

Each material record must keep its source type and source file or URL. Source links in the UI should prefer the vendor source page and vendor PDF when available, plus the local datasheet path.

Observations must retain:

- raw label
- raw value
- raw unit
- canonical unit
- normalized min, max, and nominal values where numeric
- test method, orientation, and condition when discoverable
- source context
- quality flags

## Unit Policy

Internal canonical units remain ASCII for stable parsing and storage:

- temperatures: `degC`
- density: `g/cm3`
- melt volume rate: `cm3/10min`
- max volumetric speed: `mm3/s`
- Charpy impact: `kJ/m2`
- Izod impact: `J/m`
- resistance: `ohm`, `ohm/sq`

Visible UI/report units must use scientific symbols:

- `°C`
- `g/cm³`
- `cm³/10 min`
- `mm³/s`
- `kJ/m²`
- `J/m²`
- `Ω`
- `Ω/sq`

## UI Requirements

The browser UI must support light and dark modes, distinct material colors, hover details for visual elements, source links on detail pages, and progressive disclosure of advanced extraction context.

Charts and summary metrics must use only published values that pass validation. Suspect values must not influence radar, spread, fingerprint, or material-map visualizations.

## Acceptance Criteria

- Prusament PLA and Prusament PLA Blend density publish as `1.24 g/cm³`, not `3 g/cm³`.
- No published value is captured from unit exponents such as `g/cm³`, `cm³`, `m²`, or broken `g/cm | 3`.
- Nozzle, bed, chamber, impact, density, and modulus values pass property-specific plausibility rules.
- Rejected candidates are available in audit JSON and Markdown output.
- UI visible units use scientific symbols consistently.
- The test suite and strict database audit pass after rebuilding the database.
