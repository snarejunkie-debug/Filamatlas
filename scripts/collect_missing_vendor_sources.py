from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

try:
    import urllib3
except Exception:  # pragma: no cover
    urllib3 = None


ROOT = Path(__file__).resolve().parents[1]
DATASHEET_ROOT = ROOT / "filament_datasheets"
MANIFEST_DIR = DATASHEET_ROOT / "_manifest"
TARGETS_PATH = MANIFEST_DIR / "vendor_extraction_targets.json"
HTML_SPECS_PATH = MANIFEST_DIR / "html_material_specs.json"
RUN_CSV_PATH = MANIFEST_DIR / "missing_vendor_extraction_run.csv"

UNSCRUBBED_STATUSES = {"present_partial", "missing", "manifest_gap", "needs_discovery"}
INSECURE_SSL_HOSTS = {"wiki.overture3d.com"}

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (compatible; filament-database-extractor/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
    }
)

MATERIAL_KEYWORDS = (
    "filament",
    "pla",
    "petg",
    "abs",
    "asa",
    "tpu",
    "tpe",
    "pa",
    "nylon",
    "pc",
    "hips",
    "pva",
    "pp",
    "cpe",
    "pctg",
    "carbon",
    "cf",
    "gf",
    "silk",
    "matte",
    "wood",
)

HARD_EXCLUDE_PRODUCT_KEYWORDS = (
    "dryer",
    "dry box",
    "resin",
    "nozzle",
    "hotend",
    "build plate",
    "heater",
    "accessor",
    "adapter",
    "replacement",
    "wash",
    "cure",
    "scanner",
    "laser",
    "vacuum storage",
    "storage bag",
)

EXCLUDE_PRODUCT_KEYWORDS = (
    "combo",
    "centauri",
    "kobra",
    "neptune",
    "mars",
    "saturn",
    "jupiter",
    "mercury",
    "photon",
)

PRODUCT_LIMITS = {
    "Anycubic": 35,
    "ColorFabb": 30,
    "Creality": 40,
    "Elegoo": 35,
    "Hatchbox": 30,
    "MatterHackers": 30,
    "SUNLU": 30,
}

EXTRA_SEEDS = {
    "Anycubic": ["https://store.anycubic.com/collections/filaments"],
    "ColorFabb": ["https://colorfabb.us/filaments"],
    "SUNLU": ["https://www.sunlu.com/collections/3d-filaments"],
}

TDS_MARKERS = (
    "tds",
    "technical data sheet",
    "technical-data-sheet",
    "technical_data_sheet",
    "technical datasheet",
)

PDF_SKIP_MARKERS = (
    "sds",
    "msds",
    "safety data",
    "safety-data",
    "safety_data",
    "guide",
    "manual",
    "rohs",
    "reach",
    "certificate",
    "certification",
    "declaration",
    "catalog",
    "brochure",
)

LABEL_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Diameter Tolerance", (r"dimensional accuracy", r"diameter tolerance", r"filament tolerance", r"\btolerance\b")),
    ("Diameter", (r"filament diameter", r"\bdiameter\b")),
    ("Net Weight", (r"net (?:filament )?weight", r"filament weight", r"spool net weight", r"\bweight\b")),
    ("Filament Length", (r"filament length", r"line length")),
    ("Nozzle Temperature", (r"nozzle temperature", r"printing temperature", r"print temperature", r"extrusion temperature", r"extruder temperature")),
    ("Bed Temperature", (r"bed temperature", r"build plate temperature", r"heated bed", r"hot bed")),
    ("Print Speed", (r"print speed", r"printing speed")),
    ("Density", (r"specific gravity", r"\bdensity\b")),
    ("Melt Flow Index", (r"melt flow index", r"melt flow rate", r"melt index", r"\bmfr\b", r"\bmfi\b")),
    ("Tensile Strength", (r"tensile strength", r"tensile stress")),
    ("Tensile Modulus", (r"tensile modulus", r"young'?s modulus")),
    ("Elongation", (r"elongation at break", r"breaking elongation", r"\belongation\b")),
    ("Flexural Strength", (r"flexural strength", r"bending strength")),
    ("Flexural Modulus", (r"flexural modulus", r"bending modulus")),
    ("Charpy Impact Strength", (r"charpy",)),
    ("Izod Impact Strength", (r"izod",)),
    ("Impact Strength", (r"impact strength",)),
    ("Hardness Shore D", (r"shore d", r"shore hardness d")),
    ("Hardness Shore A", (r"shore a", r"shore hardness a")),
    ("Heat Distortion Temperature", (r"heat distortion", r"heat deflection", r"thermal deformation", r"\bhdt\b")),
    ("Vicat Softening Temperature", (r"vicat",)),
    ("Glass Transition Temperature", (r"glass transition", r"\btg\b")),
    ("Melting Temperature", (r"melting point", r"melting temperature", r"\btm\b")),
    ("Water Absorption", (r"water absorption", r"moisture absorption")),
    ("Shrinkage", (r"shrinkage",)),
)


def clean_space(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.replace("\u00b1", "+/-").replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u223c", "~").replace("\uff5e", "~")
    text = text.replace("\u2103", " C").replace("\u00b0C", " C").replace("\u00b0F", " F")
    text = text.replace("mm / s", "mm/s").replace("mm /sec", "mm/s").replace("mm/s.", "mm/s")
    text = text.replace("g / cm3", "g/cm3").replace("g/cm\u00b3", "g/cm3").replace("g / 10 min", "g/10min")
    text = re.sub(r"(?<=\d)\s*~\s*(?=\d)", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def ascii_filename(text: str, max_len: int = 145) -> str:
    text = unquote(text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9._()+& -]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .-_")
    return (text[:max_len].strip(" .-_") or "document")


def normalize_url(url: str, keep_query: bool = True) -> str:
    parsed = urlparse(url)
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))


def fetch(url: str) -> requests.Response:
    host = urlparse(url).netloc.lower()
    verify = host not in INSECURE_SSL_HOSTS
    if not verify and urllib3:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = SESSION.get(url, timeout=45, allow_redirects=True, verify=verify)
    response.raise_for_status()
    return response


def html_soup(response: requests.Response) -> BeautifulSoup:
    response.encoding = response.encoding or response.apparent_encoding or "utf-8"
    return BeautifulSoup(response.text, "html.parser")


def page_links(soup: BeautifulSoup, base_url: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = normalize_url(urljoin(base_url, href), keep_query=True)
        text = clean_space(anchor.get_text(" ", strip=True))
        links.append((text, url))
    return links


def title_from_soup(soup: BeautifulSoup, fallback_url: str) -> str:
    h1 = soup.find("h1")
    if h1 and clean_space(h1.get_text(" ", strip=True)):
        title = clean_space(h1.get_text(" ", strip=True))
    else:
        meta = soup.find("meta", attrs={"property": "og:title"}) or soup.find("meta", attrs={"name": "twitter:title"})
        title = clean_space(str(meta.get("content"))) if meta and meta.get("content") else ""
    if not title and soup.title:
        title = clean_space(soup.title.get_text(" ", strip=True))
    if not title:
        title = Path(urlparse(fallback_url).path).stem.replace("-", " ")
    title = re.sub(r"\s*[|\-]\s*(SUNLU|ELEGOO|Anycubic|HATCHBOX|Creality Store|ColorFabb|Fillamentum).*$", "", title, flags=re.I)
    return clean_space(title)


def is_pdfish(url: str) -> bool:
    parsed = urlparse(url)
    hay = f"{parsed.path} {parsed.query}".lower()
    return ".pdf" in hay or "filename=tds" in hay


def is_tds_pdf_link(link_text: str, url: str) -> bool:
    hay = clean_space(f"{link_text} {unquote(url)}").lower().replace("_", " ").replace("-", " ")
    if not is_pdfish(url):
        return False
    if any(marker in hay for marker in PDF_SKIP_MARKERS):
        return False
    return any(marker.replace("-", " ") in hay for marker in TDS_MARKERS) or "filename=tds" in hay


def pdf_label(page_title: str, link_text: str, url: str) -> str:
    parsed_name = Path(unquote(urlparse(url).path)).stem.replace("_", " ").replace("-", " ")
    parts = [part for part in (page_title, link_text, parsed_name) if part]
    label = " ".join(dict.fromkeys(clean_space(part) for part in parts))
    label = re.sub(r"\b(download|view|open)\b", "", label, flags=re.I)
    label = clean_space(label)
    if not re.search(r"\btds\b|technical", label, re.I):
        label = f"{label} technical_datasheet"
    return label


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    for idx in range(2, 1000):
        candidate = path.with_name(f"{stem} ({idx}){path.suffix}")
        if not candidate.exists():
            return candidate
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:8]
    return path.with_name(f"{stem}-{digest}{path.suffix}")


def download_pdf(vendor: str, page_url: str, page_title: str, link_text: str, pdf_url: str, run_rows: list[dict[str, str]]) -> str | None:
    vendor_dir = DATASHEET_ROOT / vendor
    vendor_dir.mkdir(parents=True, exist_ok=True)
    label = pdf_label(page_title, link_text, pdf_url)
    filename = f"{vendor} - {ascii_filename(label)}.pdf"
    out_path = vendor_dir / filename
    if out_path.exists():
        rel = out_path.relative_to(ROOT).as_posix()
        log(run_rows, vendor, page_url, "download_pdf", "exists", pdf_url, rel)
        return rel
    try:
        response = fetch(pdf_url)
    except Exception as exc:
        log(run_rows, vendor, pdf_url, "download_pdf", "error", f"{type(exc).__name__}: {exc}")
        return None
    content = response.content
    content_type = response.headers.get("content-type", "")
    if not content.lstrip().startswith(b"%PDF") and "pdf" not in content_type.lower():
        log(run_rows, vendor, pdf_url, "download_pdf", "not_pdf", content_type or "missing content-type")
        return None
    out_path.write_bytes(content)
    rel = out_path.relative_to(ROOT).as_posix()
    log(run_rows, vendor, page_url, "download_pdf", "saved", pdf_url, rel)
    return rel


def is_product_page_url(vendor: str, url: str, link_text: str = "") -> bool:
    parsed = urlparse(url)
    path = unquote(parsed.path).lower()
    hay = clean_space(f"{path} {link_text}").lower().replace("-", " ")
    if any(skip in hay for skip in HARD_EXCLUDE_PRODUCT_KEYWORDS):
        return False
    if any(skip in hay for skip in EXCLUDE_PRODUCT_KEYWORDS) and "filament" not in hay:
        return False
    if vendor == "ColorFabb":
        if path.strip("/") in {"", "catalogue", "filaments", "materials"}:
            return False
        if path.startswith("/filaments/effects"):
            return False
        if path.startswith("/filaments/") and not path.startswith("/filaments/materials/"):
            return False
        return (
            path.startswith("/filaments/materials/")
            or any(keyword in hay for keyword in MATERIAL_KEYWORDS)
        ) and "/blog" not in path
    if "/products/" in path:
        return any(keyword in hay for keyword in MATERIAL_KEYWORDS)
    if vendor == "MatterHackers" and "/store/l/" in path:
        return any(keyword in hay for keyword in MATERIAL_KEYWORDS)
    return False


def canonical_label(label: str) -> str | None:
    low = clean_space(label).lower()
    if not low or len(low) > 90:
        return None
    if any(word in low for word in ("package", "gross", "carton", "shipping")) and "net" not in low:
        return None
    if "spool weight" in low and "net" not in low:
        return None
    if "inner diameter" in low or "outer diameter" in low:
        return None
    if any(word in low for word in ("price", "sku", "barcode", "review", "warranty", "brand", "color", "proposition", "warning")):
        return None
    for canonical, patterns in LABEL_RULES:
        if any(re.search(pattern, low, re.I) for pattern in patterns):
            return canonical
    return None


def label_unit_hint(label: str) -> str | None:
    m = re.search(r"\(([^)]+)\)", label)
    if not m:
        return None
    unit = clean_space(m.group(1))
    if re.search(r"^(MPa|GPa|kPa|Pa|psi|ksi|mm|m|kg|g|%|g/cm3|g/10min|mm/s|C|F)$", unit, re.I):
        return unit
    return None


def value_has_unit(value: str) -> bool:
    return bool(re.search(r"(MPa|GPa|kPa|Pa|psi|ksi|mm/s|mm3/s|mm|kg|g\b|%|g/cm|g/cc|g/10|min| C\b| F\b|Shore)", value, re.I))


def normalize_value(label: str, value: str) -> str:
    value = clean_space(value)
    unit = label_unit_hint(label)
    if unit and not value_has_unit(value):
        value = f"{value} {unit}"
    value = re.sub(r"(?<=\d)\s*/\s*10\s*min", "/10min", value, flags=re.I)
    value = re.sub(r"(?<=\d)\s*C\b", " C", value)
    value = re.sub(r"(?<=\d)\s*F\b", " F", value)
    return clean_space(value)


def looks_like_value(value: str) -> bool:
    value = clean_space(value)
    if not value or len(value) > 160:
        return False
    low = value.lower()
    if re.search(r"[$]\s*\d", value):
        return False
    if any(word in low for word in ("proposition", "warning", "warranty", "shipping", "delivery", "refund", "return", "discount", "coupon", "sold out")):
        return False
    numeric_probe = re.sub(r"\b3d\b", "", low)
    return bool(re.search(r"\d", numeric_probe) or re.search(r"\b(HB|V-0|V-1|V-2|Shore)\b", value, re.I))


def append_row(rows: list[str], seen: set[str], label: str, value: str, context: str = "official_html_specs") -> None:
    canon = canonical_label(label)
    if not canon:
        return
    low_label = clean_space(label).lower()
    if canon == "Diameter" and ("spool" in low_label or "inner diameter" in low_label or "outer diameter" in low_label):
        return
    if canon == "Net Weight" and "spool weight" in low_label and "net" not in low_label:
        return
    value = normalize_value(label, value)
    if not looks_like_value(value):
        return
    row = clean_space(f"{canon} | {value} | {context}")
    key = row.lower()
    if key not in seen:
        seen.add(key)
        rows.append(row)


def table_rows(soup: BeautifulSoup, rows: list[str], seen: set[str]) -> None:
    for tr in soup.find_all("tr"):
        cells = [clean_space(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        cells = [cell for cell in cells if cell]
        if len(cells) >= 2:
            append_row(rows, seen, cells[0], " | ".join(cells[1:]))


def definition_rows(soup: BeautifulSoup, rows: list[str], seen: set[str]) -> None:
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd:
            append_row(rows, seen, dt.get_text(" ", strip=True), dd.get_text(" ", strip=True))


def text_line_rows(soup: BeautifulSoup, rows: list[str], seen: set[str]) -> None:
    lines = [clean_space(line) for line in soup.get_text("\n", strip=True).splitlines()]
    lines = [line for line in lines if line and len(line) <= 180]
    for i, line in enumerate(lines):
        if re.search(r"(add to cart|newsletter|cookie|shipping|tax|qty|quantity|sold out)", line, re.I):
            continue
        split = re.match(r"^(.{3,85}?)(?:[:：]\s+|\s{2,}|\s+[|]\s+)(.+)$", line)
        if split:
            append_row(rows, seen, split.group(1), split.group(2))
        for canonical, patterns in LABEL_RULES:
            for pattern in patterns:
                m = re.search(pattern, line, re.I)
                if not m:
                    continue
                tail = line[m.end() :].strip(" :：|-")
                if looks_like_value(tail):
                    append_row(rows, seen, canonical, tail)
        canon = canonical_label(line)
        if canon and i + 1 < len(lines):
            append_row(rows, seen, canon, lines[i + 1])


def title_rows(product: str, rows: list[str], seen: set[str]) -> None:
    for m in re.finditer(r"\b(1\.75|2\.85|3\.0|3\.00)\s*mm\b", product, re.I):
        append_row(rows, seen, "Diameter", f"{m.group(1)} mm", "official_html_title")
    weight_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(kg|g)\b", product, re.I)
    if weight_match:
        append_row(rows, seen, "Net Weight", f"{weight_match.group(1)} {weight_match.group(2)}", "official_html_title")


def extract_html_rows(soup: BeautifulSoup, product: str) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    title_rows(product, rows, seen)
    table_rows(soup, rows, seen)
    definition_rows(soup, rows, seen)
    text_line_rows(soup, rows, seen)
    return rows


def save_html_snapshot(vendor: str, product: str, html: str) -> str:
    vendor_dir = DATASHEET_ROOT / vendor
    vendor_dir.mkdir(parents=True, exist_ok=True)
    out_path = vendor_dir / f"{vendor} - {ascii_filename(product)} - product_page.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path.relative_to(ROOT).as_posix()


def log(
    run_rows: list[dict[str, str]],
    vendor: str,
    source_url: str,
    action: str,
    status: str,
    detail: str = "",
    output_file: str = "",
) -> None:
    run_rows.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vendor": vendor,
            "source_url": source_url,
            "action": action,
            "status": status,
            "detail": detail,
            "output_file": output_file,
        }
    )


def process_html_page(
    vendor: str,
    url: str,
    soup: BeautifulSoup,
    html: str,
    html_entries: list[dict[str, object]],
    run_rows: list[dict[str, str]],
) -> None:
    if not is_product_page_url(vendor, url):
        return
    source_url = normalize_url(url, keep_query=False)
    if any(entry.get("source_url") == source_url for entry in html_entries):
        log(run_rows, vendor, source_url, "extract_html_specs", "duplicate", "already captured")
        return
    product = title_from_soup(soup, url)
    rows = extract_html_rows(soup, product)
    if not rows:
        log(run_rows, vendor, url, "extract_html_specs", "no_rows", product)
        return
    rel = save_html_snapshot(vendor, product, html)
    html_entries.append(
        {
            "supplier": vendor,
            "product": product,
            "source_type": "official_html_specs",
            "source_url": source_url,
            "source_file": rel,
            "rows": rows,
            "text": "\n".join([product, *rows]),
        }
    )
    log(run_rows, vendor, source_url, "extract_html_specs", "saved", f"{len(rows)} rows", rel)


def colorfabb_material_facets(soup: BeautifulSoup) -> list[dict[str, str]]:
    facets: list[dict[str, str]] = []
    seen: set[str] = set()
    for input_el in soup.select('input[name="amshopby[material][]"]'):
        li = input_el.find_parent("li")
        label = clean_space(str(li.get("data-label") or "")) if li else ""
        if not label:
            label_el = li.find(class_="label") if li else None
            label = clean_space(label_el.get_text(" ", strip=True)) if label_el else ""
        if not label or label.lower() in seen:
            continue
        init_el = input_el.find_parent(attrs={"data-mage-init": True})
        init = str(init_el.get("data-mage-init") or "") if init_el else ""
        url_match = re.search(r"https:\\/\\/[^\"}]+", init)
        facet_url = url_match.group(0).replace("\\/", "/") if url_match else ""
        if not facet_url:
            facet_url = f"https://colorfabb.us/filaments/{label.lower().replace(' ', '_').replace('-', '_')}"
        seen.add(label.lower())
        facets.append({"label": label, "url": normalize_url(facet_url, keep_query=False)})
    return facets


def product_links_from_listing(soup: BeautifulSoup, base_url: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("a.product-item-link"):
        href = str(anchor.get("href") or "").strip()
        if not href:
            continue
        url = normalize_url(urljoin(base_url, href), keep_query=False)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def process_colorfabb(html_entries: list[dict[str, object]], run_rows: list[dict[str, str]]) -> None:
    vendor = "ColorFabb"
    seed_url = "https://colorfabb.us/filaments"
    try:
        response = fetch(seed_url)
    except Exception as exc:
        log(run_rows, vendor, seed_url, "fetch_seed", "error", f"{type(exc).__name__}: {exc}")
        return
    soup = html_soup(response)
    facets = colorfabb_material_facets(soup)
    log(run_rows, vendor, seed_url, "extract_material_facets", "ok", f"{len(facets)} facets")

    existing_urls = {entry.get("source_url") for entry in html_entries}
    for facet in facets:
        label = facet["label"]
        facet_url = facet["url"]
        if facet_url in existing_urls:
            log(run_rows, vendor, facet_url, "extract_html_specs", "duplicate", label)
            continue
        rows: list[str] = []
        seen_rows: set[str] = set()
        snapshot_html = ""
        snapshot_title = label
        try:
            listing_response = fetch(facet_url)
            listing_soup = html_soup(listing_response)
            product_urls = product_links_from_listing(listing_soup, listing_response.url)
            log(run_rows, vendor, facet_url, "fetch_material_facet", "ok", f"{len(product_urls)} products")
        except Exception as exc:
            product_urls = []
            log(run_rows, vendor, facet_url, "fetch_material_facet", "error", f"{type(exc).__name__}: {exc}")

        for product_url in product_urls[:3]:
            try:
                product_response = fetch(product_url)
            except Exception as exc:
                log(run_rows, vendor, product_url, "fetch_product", "error", f"{type(exc).__name__}: {exc}")
                continue
            product_soup = html_soup(product_response)
            product_title = title_from_soup(product_soup, product_url)
            for link_text, link_url in page_links(product_soup, product_response.url):
                if is_tds_pdf_link(link_text, link_url):
                    download_pdf(vendor, product_response.url, product_title, link_text, link_url, run_rows)
            for row in extract_html_rows(product_soup, product_title):
                key = row.lower()
                if key not in seen_rows:
                    seen_rows.add(key)
                    rows.append(row)
            if not snapshot_html:
                snapshot_html = product_response.text
                snapshot_title = label

        if snapshot_html:
            rel = save_html_snapshot(vendor, snapshot_title, snapshot_html)
        else:
            rel = ""
        html_entries.append(
            {
                "supplier": vendor,
                "product": label,
                "source_type": "official_html_specs",
                "source_url": facet_url,
                "source_file": rel,
                "rows": rows,
                "text": "\n".join([label, *rows]),
            }
        )
        existing_urls.add(facet_url)
        log(run_rows, vendor, facet_url, "extract_html_specs", "saved", f"{len(rows)} rows", rel)


def process_vendor(target: dict[str, object], html_entries: list[dict[str, object]], run_rows: list[dict[str, str]]) -> None:
    vendor = str(target.get("vendor") or "").strip()
    if not vendor:
        return
    status = str(target.get("status") or "")
    if status not in UNSCRUBBED_STATUSES:
        return
    if vendor == "ColorFabb":
        process_colorfabb(html_entries, run_rows)
        return
    seed_urls = [str(url) for url in target.get("source_urls", []) if isinstance(url, str)]
    seed_urls.extend(EXTRA_SEEDS.get(vendor, []))
    if vendor == "Anycubic":
        seed_urls = [url.replace("/collections/filament", "/collections/filaments") for url in seed_urls]

    seen_pages: set[str] = set()
    product_urls: list[str] = []
    product_seen: set[str] = set()
    limit = PRODUCT_LIMITS.get(vendor, 25)

    for seed_url in dict.fromkeys(seed_urls):
        try:
            response = fetch(seed_url)
        except Exception as exc:
            log(run_rows, vendor, seed_url, "fetch_seed", "error", f"{type(exc).__name__}: {exc}")
            continue
        soup = html_soup(response)
        title = title_from_soup(soup, seed_url)
        log(run_rows, vendor, seed_url, "fetch_seed", "ok", title)
        for link_text, link_url in page_links(soup, response.url):
            if is_tds_pdf_link(link_text, link_url):
                download_pdf(vendor, response.url, title, link_text, link_url, run_rows)
            if is_product_page_url(vendor, link_url, link_text):
                product_key = normalize_url(link_url, keep_query=False)
                if product_key not in product_seen:
                    product_seen.add(product_key)
                    product_urls.append(product_key)
        process_html_page(vendor, normalize_url(response.url, keep_query=False), soup, response.text, html_entries, run_rows)

    for product_url in product_urls[:limit]:
        if product_url in seen_pages:
            continue
        seen_pages.add(product_url)
        try:
            response = fetch(product_url)
        except Exception as exc:
            log(run_rows, vendor, product_url, "fetch_product", "error", f"{type(exc).__name__}: {exc}")
            continue
        soup = html_soup(response)
        title = title_from_soup(soup, product_url)
        log(run_rows, vendor, product_url, "fetch_product", "ok", title)
        for link_text, link_url in page_links(soup, response.url):
            if is_tds_pdf_link(link_text, link_url):
                download_pdf(vendor, response.url, title, link_text, link_url, run_rows)
        process_html_page(vendor, normalize_url(response.url, keep_query=False), soup, response.text, html_entries, run_rows)


def write_outputs(html_entries: list[dict[str, object]], run_rows: list[dict[str, str]]) -> None:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).date().isoformat(),
        "source": "scripts/collect_missing_vendor_sources.py",
        "entries": html_entries,
    }
    HTML_SPECS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with RUN_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["timestamp", "vendor", "source_url", "action", "status", "detail", "output_file"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(run_rows)


def main() -> None:
    targets = json.loads(TARGETS_PATH.read_text(encoding="utf-8")).get("targets", [])
    html_entries: list[dict[str, object]] = []
    run_rows: list[dict[str, str]] = []
    for target in targets:
        if isinstance(target, dict):
            process_vendor(target, html_entries, run_rows)
    write_outputs(html_entries, run_rows)
    summary: dict[str, dict[str, int]] = {}
    for row in run_rows:
        vendor = row["vendor"]
        bucket = summary.setdefault(vendor, {})
        key = f"{row['action']}:{row['status']}"
        bucket[key] = bucket.get(key, 0) + 1
    print(json.dumps({"html_entries": len(html_entries), "run_rows": len(run_rows), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
