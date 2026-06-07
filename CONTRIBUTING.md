# Contributing

Thanks for helping test Filament Material Atlas. The most useful early feedback is precise, source-backed, and easy to reproduce.

## Good Feedback

- UI bugs: include what you clicked, what looked wrong, browser/device, and whether light or dark mode was active.
- Data corrections: include the material, supplier, property, expected value, unit, and vendor source URL.
- Feature ideas: describe the workflow you were trying to complete, not only the control you want added.

## Source Material

Please link to official vendor pages or PDFs instead of attaching copied documents. The public repository intentionally avoids committing the raw downloaded datasheet corpus.

## Local Checks

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests
python -m http.server 8000
```

Then open `http://localhost:8000/web/`.

## Pull Requests

Keep pull requests focused. For data parser changes, include a test fixture or describe which source row motivated the change. For UI changes, include before/after notes and check both desktop and mobile widths.

