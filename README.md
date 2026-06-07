# Filament Material Atlas

Filament Material Atlas is a static, source-backed browser tool for comparing FFF/FDM filament materials. It ships with a generated public data snapshot in `web/data/materials.json`, plus source metadata that links records back to vendor pages or PDFs when available.

## Try It Locally

Run a simple static server from the repository root:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/web/
```

Opening `web/index.html` directly may work for layout checks, but a local server is better because the app loads JSON and source metadata with `fetch()`.

## Publish to GitHub Pages

This repo includes `.github/workflows/pages.yml`, which validates the Python tests and deploys the static site from `web/`.

1. Create an empty GitHub repository.
2. Push this repository to `main`.
3. In GitHub, open `Settings > Pages` and choose `GitHub Actions` as the source if GitHub has not selected it automatically.
4. Share the Pages URL once the `Validate and Deploy Site` workflow completes.

The app can infer `owner/repo` on normal GitHub Pages project URLs like `https://owner.github.io/repo/`. If you use a custom domain, set `githubRepo` in `web/site-config.js` to `"owner/repo"` so the in-app feedback buttons open prefilled GitHub issues.

## Feedback Flow

Users can file feedback in two ways:

- Use the small bug buttons inside the atlas UI. On GitHub Pages, these open a prefilled GitHub issue with the selected material, current filters, chart state, and note.
- Open a new issue from the repository and choose one of the templates for bugs, material data corrections, or feature ideas.

For material corrections, ask users to include a vendor source URL and the exact value they expected. Please avoid attaching copied vendor PDFs unless their license clearly permits redistribution.

## Public Data Policy

The initial upload is intentionally lightweight:

- Included: static site files, generated public material JSON, source metadata manifests, scripts, tests, and project docs.
- Excluded: raw downloaded vendor PDFs/HTML pages, SQLite databases, screenshots, and generated analysis dumps.

This keeps the public repo useful for feedback without redistributing a large mirrored vendor corpus.

## Development

Install test dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run the tests:

```bash
python -m unittest discover -s tests
```

The parser/build scripts expect the raw `filament_datasheets/` corpus for full database regeneration. Public clones can still inspect and test the published snapshot.

## License

This project is licensed under the MIT License. The license applies to the project code, UI, scripts, documentation, and database curation. Vendor datasheets and third-party source material remain governed by their original owners and are not redistributed in this repository.
