# Filament Datasheet Corpus

This folder is a seed corpus for building a 1.75 mm FDM filament materials database.

## Layout

- Vendor folders contain downloaded technical data sheets, material data sheets, and closely related product specification PDFs.
- `_manifest/filament_datasheets.csv` records one row per attempted datasheet with source URL, local path, document type, and status.
- `_manifest/vendor_sources.md` records source pages that are useful for future scraping or manual expansion.

## File Naming

Use readable, stable names:

`Vendor - Product - Material - DocumentType.pdf`

When the vendor already publishes a generic family-level sheet, use the family name instead of inventing a product variant.

## Database Extraction Targets

Good first-pass fields to extract from the PDFs:

- Vendor
- Product name
- Material family
- Filament diameter
- Color or variant scope
- Print temperature
- Bed temperature
- Chamber or enclosure recommendation
- Drying recommendation
- Density
- Tensile strength
- Tensile modulus
- Elongation at break
- Flexural strength
- Flexural modulus
- Impact strength
- Heat deflection temperature
- Vicat softening temperature
- Shore hardness
- Melt flow index
- Certifications or standards
- Source document path and URL

Keep values tied to source documents because vendors use different test standards, print settings, annealing conditions, and specimen orientations.
