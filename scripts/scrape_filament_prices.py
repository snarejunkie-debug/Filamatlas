from __future__ import annotations

import csv
import json
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DATASHEET_ROOT = ROOT / "filament_datasheets"
MANIFEST_DIR = DATASHEET_ROOT / "_manifest"
HTML_SPECS_PATH = MANIFEST_DIR / "html_material_specs.json"
TARGETS_PATH = MANIFEST_DIR / "vendor_extraction_targets.json"
OUT_JSON = MANIFEST_DIR / "filament_current_prices.json"
OUT_CSV = MANIFEST_DIR / "filament_current_prices.csv"
RUN_CSV = MANIFEST_DIR / "filament_price_scrape_run.csv"
EXCHANGE_RATE_SOURCE = "https://api.frankfurter.dev/v2/rate/{base}/USD"

SCRAPED_AT = datetime.now(timezone.utc).isoformat()

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (compatible; filament-price-scraper/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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
    "nylon",
    "pa",
    "pc",
    "pp",
    "pva",
    "hips",
    "pctg",
    "cpe",
    "carbon",
    "cf",
    "gf",
    "silk",
    "matte",
    "wood",
)

HARD_EXCLUDE_KEYWORDS = (
    "resin",
    "nozzle",
    "hotend",
    "dryer",
    "dry box",
    "storage bag",
    "vacuum storage",
    "adapter",
    "replacement",
    "accessory",
    "scanner",
    "laser",
    "wash",
    "cure",
)

SOFT_EXCLUDE_KEYWORDS = ("printer",)

SHOPIFY_SITEMAPS = {
    "Anycubic": "https://store.anycubic.com/sitemap_products_1.xml",
    "Bambu Lab": "https://us.store.bambulab.com/sitemap_products_1.xml",
    "Creality": "https://store.creality.com/sitemap_products_1.xml",
    "Elegoo": "https://www.elegoo.com/sitemap_products_1.xml",
    "eSUN": "https://esun3dstore.com/sitemap_products_1.xml",
    "Fillamentum": "https://fillamentum.com/sitemap_products_1.xml",
    "Hatchbox": "https://www.hatchbox3d.com/sitemap_products_1.xml",
    "Polymaker": "https://shop.polymaker.com/sitemap_products_1.xml",
    "SUNLU": "https://www.sunlu.com/sitemap_products_1.xml",
    "UltiMaker": "https://store.ultimaker.com/sitemap_products_1.xml",
}

EXTRA_SEEDS = {
    "3DXTech": ["https://www.3dxtech.com/"],
    "Bambu Lab": ["https://us.store.bambulab.com/collections/filament"],
    "ColorFabb": ["https://colorfabb.com/catalogue"],
    "MatterHackers": [
        "https://www.matterhackers.com/store/c/mh-build-series-pla",
        "https://www.matterhackers.com/store/c/mh-build-series-petg",
        "https://www.matterhackers.com/store/c/pro-series-pla",
    ],
    "Polymaker": ["https://shop.polymaker.com/collections/all"],
    "Prusa Polymers": [
        "https://prusament.com/materials/pla/",
        "https://prusament.com/materials/petg/",
        "https://prusament.com/materials/asa/",
        "https://prusament.com/materials/pc-blend/",
        "https://prusament.com/materials/pa11-cf/",
    ],
    "UltiMaker": ["https://store.ultimaker.com/collections/materials"],
}

PRODUCT_LIMITS = {
    "3DXTech": 80,
    "Anycubic": 80,
    "Bambu Lab": 80,
    "ColorFabb": 80,
    "Creality": 80,
    "Elegoo": 100,
    "eSUN": 80,
    "Fillamentum": 80,
    "Hatchbox": 80,
    "MatterHackers": 80,
    "Polymaker": 100,
    "Prusa Polymers": 40,
    "SUNLU": 80,
    "UltiMaker": 80,
}

VENDOR_DEFAULT_CURRENCY = {
    "3DXTech": "USD",
    "Anycubic": "USD",
    "Bambu Lab": "USD",
    "ColorFabb": "EUR",
    "Creality": "USD",
    "Elegoo": "USD",
    "eSUN": "USD",
    "Fillamentum": "EUR",
    "Hatchbox": "USD",
    "MatterHackers": "USD",
    "Polymaker": "USD",
    "Prusa Polymers": "EUR",
    "SUNLU": "USD",
    "UltiMaker": "USD",
}


@dataclass
class Candidate:
    vendor: str
    url: str
    hint_product: str = ""
    source: str = ""


def load_sidecar_mass_by_url() -> dict[str, tuple[float, str]]:
    if not HTML_SPECS_PATH.exists():
        return {}
    data = json.loads(HTML_SPECS_PATH.read_text(encoding="utf-8"))
    out: dict[str, tuple[float, str]] = {}
    for entry in data.get("entries", []):
        url = entry.get("source_url")
        if not url:
            continue
        probes = [str(entry.get("product") or "")]
        for row in entry.get("rows", []):
            if re.search(r"^(Net Weight|Diameter|Filament Length)\s*\|", str(row), re.I):
                probes.append(str(row))
        candidates: list[tuple[float, str]] = []
        for probe in probes:
            candidates.extend(mass_candidates(probe))
        if candidates:
            kg, raw = sorted(candidates, key=lambda x: x[0], reverse=True)[0]
            out[normalize_url(str(url))] = (round(kg, 6), f"html_sidecar:{raw}")
    return out


SIDECAR_MASS_BY_URL: dict[str, tuple[float, str]] | None = None


def clean_space(text: str) -> str:
    text = str(text or "").replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_url(url: str, keep_query: bool = False) -> str:
    parsed = urlparse(url)
    query = parsed.query if keep_query else ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") or "/", "", query, ""))


def fetch(url: str) -> requests.Response:
    response = SESSION.get(url, timeout=35, allow_redirects=True)
    response.raise_for_status()
    return response


def fetch_usd_exchange_rates(currencies: set[str]) -> dict[str, dict[str, object]]:
    rates: dict[str, dict[str, object]] = {
        "USD": {
            "rate": 1.0,
            "date": SCRAPED_AT[:10],
            "source": "identity",
        }
    }
    for currency in sorted(c for c in currencies if c and c != "USD"):
        endpoint = EXCHANGE_RATE_SOURCE.format(base=currency)
        response = fetch(endpoint)
        data = response.json()
        rate = float(data["rate"])
        rates[currency] = {
            "rate": rate,
            "date": str(data.get("date") or ""),
            "source": endpoint,
        }
    return rates


def add_usd_conversions(rows: list[dict[str, object]], rates: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    for row in rows:
        currency = clean_space(row.get("currency") or "")
        info = rates.get(currency)
        if not info:
            row["exchange_rate_to_usd"] = None
            row["exchange_rate_date"] = ""
            row["exchange_rate_source"] = ""
            row["price_usd"] = None
            row["price_per_kg_usd"] = None
            continue
        rate = float(info["rate"])
        row["exchange_rate_to_usd"] = rate
        row["exchange_rate_date"] = info.get("date") or ""
        row["exchange_rate_source"] = info.get("source") or ""
        price = number_or_none(row.get("price"))
        price_per_kg = number_or_none(row.get("price_per_kg"))
        row["price_usd"] = round(price * rate, 4) if price is not None else None
        row["price_per_kg_usd"] = round(price_per_kg * rate, 4) if price_per_kg is not None else None
    return rows


def shopify_product_json_url(url: str) -> str | None:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "products":
        path = "/" + "/".join(parts[:2]) + ".js"
        return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))
    return None


def soup_from_response(response: requests.Response) -> BeautifulSoup:
    response.encoding = response.encoding or response.apparent_encoding or "utf-8"
    return BeautifulSoup(response.text, "html.parser")


def title_from_soup(soup: BeautifulSoup, fallback_url: str) -> str:
    candidates: list[str] = []
    h1 = soup.find("h1")
    if h1 and clean_space(h1.get_text(" ", strip=True)):
        candidates.append(clean_space(h1.get_text(" ", strip=True)))
    meta = soup.find("meta", attrs={"property": "og:title"}) or soup.find("meta", attrs={"name": "twitter:title"})
    if meta and meta.get("content"):
        candidates.append(clean_space(meta["content"]))
    if soup.title:
        candidates.append(clean_space(soup.title.get_text(" ", strip=True)))
    candidates.append(clean_space(Path(urlparse(fallback_url).path).stem.replace("-", " ")))
    candidates = [c for c in candidates if c]
    scored = []
    for candidate in candidates:
        low = candidate.lower()
        score = len(candidate)
        if re.search(r"\b(kg|g|lb|lbs)\b", low):
            score += 100
        if "filament" in low:
            score += 50
        scored.append((score, candidate))
    return sorted(scored, reverse=True)[0][1] if scored else ""


def is_filament_url(vendor: str, url: str, text: str = "") -> bool:
    parsed = urlparse(url)
    path = unquote(parsed.path).lower()
    hay = clean_space(f"{path} {text}").lower().replace("-", " ")
    if any(skip in hay for skip in HARD_EXCLUDE_KEYWORDS):
        return False
    if any(skip in hay for skip in SOFT_EXCLUDE_KEYWORDS) and "filament" not in hay:
        return False
    if any(key in hay for key in MATERIAL_KEYWORDS):
        if "/products/" in path or "/product/" in path or "/store/l/" in path or "/materials/" in path:
            return True
        if vendor in {"ColorFabb", "Prusa Polymers"} and "/materials/" in path:
            return True
    return False


def is_filament_price_row(row: dict[str, object]) -> bool:
    hay = clean_space(" ".join(str(row.get(field) or "") for field in ("product", "variant", "url"))).lower().replace("-", " ")
    if any(skip in hay for skip in HARD_EXCLUDE_KEYWORDS):
        return False
    if hay.strip() in {"materials ultimaker", "materials ultimaker "}:
        return False
    if "materials - ultimaker" in hay:
        return False
    return any(keyword in hay for keyword in MATERIAL_KEYWORDS)


def page_product_links(vendor: str, soup: BeautifulSoup, base_url: str) -> list[Candidate]:
    out: list[Candidate] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = normalize_url(urljoin(base_url, href))
        label = clean_space(anchor.get_text(" ", strip=True))
        if is_filament_url(vendor, url, label):
            out.append(Candidate(vendor=vendor, url=url, hint_product=label, source="collection_link"))
    return out


def html_sidecar_candidates() -> list[Candidate]:
    if not HTML_SPECS_PATH.exists():
        return []
    data = json.loads(HTML_SPECS_PATH.read_text(encoding="utf-8"))
    out = []
    for entry in data.get("entries", []):
        url = entry.get("source_url")
        vendor = clean_space(entry.get("supplier"))
        if url and vendor:
            out.append(Candidate(vendor=vendor, url=normalize_url(str(url)), hint_product=clean_space(entry.get("product")), source="html_material_specs"))
    return out


def target_seed_candidates() -> list[Candidate]:
    if not TARGETS_PATH.exists():
        return []
    data = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))
    out: list[Candidate] = []
    for target in data.get("targets", []):
        vendor = clean_space(target.get("vendor"))
        for url in target.get("source_urls", []):
            if isinstance(url, str):
                out.append(Candidate(vendor=vendor, url=normalize_url(url), source="vendor_target_seed"))
        for url in EXTRA_SEEDS.get(vendor, []):
            out.append(Candidate(vendor=vendor, url=normalize_url(url), source="extra_seed"))
    for vendor, urls in EXTRA_SEEDS.items():
        for url in urls:
            out.append(Candidate(vendor=vendor, url=normalize_url(url), source="extra_seed"))
    return out


def sitemap_candidates(run_rows: list[dict[str, str]]) -> list[Candidate]:
    out: list[Candidate] = []
    for vendor, sitemap_url in SHOPIFY_SITEMAPS.items():
        try:
            response = fetch(sitemap_url)
        except Exception as exc:
            log(run_rows, vendor, sitemap_url, "sitemap", "error", f"{type(exc).__name__}: {exc}")
            continue
        try:
            root = ET.fromstring(response.content)
        except Exception as exc:
            log(run_rows, vendor, sitemap_url, "sitemap", "parse_error", f"{type(exc).__name__}: {exc}")
            continue
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [el.text or "" for el in root.findall(".//sm:loc", ns)] or [el.text or "" for el in root.findall(".//loc")]
        count = 0
        for loc in locs:
            url = normalize_url(loc)
            if is_filament_url(vendor, url):
                out.append(Candidate(vendor=vendor, url=url, source="sitemap"))
                count += 1
        log(run_rows, vendor, sitemap_url, "sitemap", "ok", f"{count} filament-ish product urls")
    return out


def discover_candidates(run_rows: list[dict[str, str]]) -> list[Candidate]:
    raw = html_sidecar_candidates()
    seeds = target_seed_candidates()
    raw.extend(sitemap_candidates(run_rows))
    for seed in seeds:
        if is_filament_url(seed.vendor, seed.url, seed.hint_product):
            raw.append(seed)
        try:
            response = fetch(seed.url)
        except Exception as exc:
            log(run_rows, seed.vendor, seed.url, "fetch_seed", "error", f"{type(exc).__name__}: {exc}")
            continue
        soup = soup_from_response(response)
        links = page_product_links(seed.vendor, soup, response.url)
        raw.extend(links)
        log(run_rows, seed.vendor, seed.url, "fetch_seed", "ok", f"{len(links)} product links")
        time.sleep(0.15)

    deduped: dict[tuple[str, str], Candidate] = {}
    for candidate in raw:
        key = (candidate.vendor, normalize_url(candidate.url))
        existing = deduped.get(key)
        if existing and existing.hint_product:
            continue
        deduped[key] = Candidate(candidate.vendor, key[1], candidate.hint_product, candidate.source)

    grouped: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in deduped.values():
        grouped[candidate.vendor].append(candidate)
    limited: list[Candidate] = []
    for vendor, candidates in grouped.items():
        candidates.sort(key=lambda c: (0 if c.source == "html_material_specs" else 1, c.url))
        limited.extend(candidates[: PRODUCT_LIMITS.get(vendor, 60)])
    return limited


def log(rows: list[dict[str, str]], vendor: str, url: str, action: str, status: str, detail: str = "") -> None:
    rows.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vendor": vendor,
            "url": url,
            "action": action,
            "status": status,
            "detail": detail,
        }
    )


def parse_json_script(text: str) -> list[object]:
    text = text.strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        return [parsed]
    except Exception:
        pass
    # JSON-LD sometimes contains several adjacent objects.
    pieces = []
    for match in re.finditer(r"\{[\s\S]*?\}", text):
        try:
            pieces.append(json.loads(match.group(0)))
        except Exception:
            continue
    return pieces


def walk_json(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def number_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        num = float(value)
    else:
        text = clean_space(str(value)).replace(",", "")
        m = re.search(r"\d+(?:\.\d+)?", text)
        if not m:
            return None
        num = float(m.group(0))
    if 0 < num < 10000:
        return num
    return None


def offer_rows_from_jsonld(soup: BeautifulSoup) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        for parsed in parse_json_script(script.get_text()):
            for node in walk_json(parsed):
                node_type = node.get("@type")
                if isinstance(node_type, list):
                    node_types = {str(x).lower() for x in node_type}
                else:
                    node_types = {str(node_type).lower()}
                if "product" not in node_types:
                    continue
                product_name = clean_space(node.get("name") or "")
                offers = node.get("offers")
                if isinstance(offers, dict):
                    offer_list = [offers]
                elif isinstance(offers, list):
                    offer_list = [offer for offer in offers if isinstance(offer, dict)]
                else:
                    offer_list = []
                for offer in offer_list:
                    price = number_or_none(offer.get("price") or offer.get("lowPrice"))
                    currency = clean_space(offer.get("priceCurrency") or "")
                    if price is None:
                        continue
                    rows.append(
                        {
                            "price": price,
                            "currency": currency,
                            "variant": clean_space(offer.get("name") or offer.get("sku") or ""),
                            "sku": clean_space(offer.get("sku") or node.get("sku") or ""),
                            "availability": clean_space(str(offer.get("availability") or "")),
                            "product_name": product_name,
                            "method": "json_ld_offer",
                        }
                    )
    return rows


def extract_balanced_array(text: str, start: int) -> str | None:
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    return None


def shopify_variant_rows(html: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen_payloads: set[str] = set()
    for match in re.finditer(r'"variants"\s*:\s*\[', html):
        start = html.find("[", match.start())
        payload = extract_balanced_array(html, start)
        if not payload or payload in seen_payloads:
            continue
        seen_payloads.add(payload)
        try:
            variants = json.loads(payload)
        except Exception:
            continue
        if not isinstance(variants, list):
            continue
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            raw_price = variant.get("price")
            price_is_cents = False
            if raw_price is None:
                raw_price = variant.get("priceInCents")
                price_is_cents = raw_price is not None
            if raw_price is None:
                continue
            try:
                price = float(raw_price) / 100 if price_is_cents or float(raw_price) > 200 else float(raw_price)
            except Exception:
                continue
            if not (0 < price < 10000):
                continue
            rows.append(
                {
                    "price": price,
                    "currency": "",
                    "variant": clean_space(variant.get("title") or variant.get("name") or ""),
                    "sku": clean_space(variant.get("sku") or ""),
                    "availability": "OutOfStock" if variant.get("available") is False or variant.get("isOutOfStock") else "InStock",
                    "product_name": "",
                    "method": "shopify_variant_json",
                }
            )
    return rows


def meta_offer_rows(soup: BeautifulSoup) -> list[dict[str, object]]:
    price = None
    for attr, val in (
        ("property", "product:price:amount"),
        ("property", "og:price:amount"),
        ("name", "twitter:data1"),
    ):
        meta = soup.find("meta", attrs={attr: val})
        if meta and meta.get("content"):
            price = number_or_none(meta.get("content"))
            if price is not None:
                break
    if price is None:
        return []
    currency = ""
    for attr, val in (("property", "product:price:currency"), ("property", "og:price:currency")):
        meta = soup.find("meta", attrs={attr: val})
        if meta and meta.get("content"):
            currency = clean_space(meta.get("content"))
            break
    return [{"price": price, "currency": currency, "variant": "", "sku": "", "availability": "", "product_name": "", "method": "meta_price"}]


def visible_price_rows(soup: BeautifulSoup) -> list[dict[str, object]]:
    # Last resort for non-structured pages such as Prusament material pages.
    text = soup.get_text("\n", strip=True)
    rows: list[dict[str, object]] = []
    for m in re.finditer(r"(?P<price>\d+(?:[.,]\d+)?)\s*(?P<currency>USD|EUR|GBP|\$|€|£)\b|(?P<symbol>[$€£])\s*(?P<price2>\d+(?:[.,]\d+)?)", text, re.I):
        price = number_or_none(m.group("price") or m.group("price2"))
        if price is None:
            continue
        currency = m.group("currency") or m.group("symbol") or ""
        currency = {"$": "USD", "€": "EUR", "£": "GBP"}.get(currency, currency.upper())
        rows.append({"price": price, "currency": currency, "variant": "", "sku": "", "availability": "", "product_name": "", "method": "visible_text_price"})
        if len(rows) >= 3:
            break
    return rows


def currency_from_html(html: str, soup: BeautifulSoup) -> str:
    for pattern in (r'"currency"\s*:\s*"([A-Z]{3})"', r'"currencyCode"\s*:\s*"([A-Z]{3})"', r'"active"\s*:\s*"([A-Z]{3})"'):
        m = re.search(pattern, html)
        if m:
            return m.group(1)
    for attr, val in (("property", "product:price:currency"), ("property", "og:price:currency")):
        meta = soup.find("meta", attrs={attr: val})
        if meta and meta.get("content"):
            return clean_space(meta.get("content")).upper()
    return ""


def dedupe_offers(offers: list[dict[str, object]], default_currency: str) -> list[dict[str, object]]:
    out = []
    seen = set()
    for offer in offers:
        price = number_or_none(offer.get("price"))
        if price is None:
            continue
        currency = clean_space(offer.get("currency") or default_currency or "")
        variant = clean_space(offer.get("variant") or "")
        sku = clean_space(offer.get("sku") or "")
        key = (round(price, 4), currency, variant, sku)
        if key in seen:
            continue
        seen.add(key)
        offer = dict(offer)
        offer["price"] = price
        offer["currency"] = currency
        out.append(offer)
    best: dict[tuple[object, ...], dict[str, object]] = {}
    best_score: dict[tuple[object, ...], int] = {}
    for offer in out:
        price = round(float(offer["price"]), 4)
        currency = clean_space(offer.get("currency") or "")
        sku = clean_space(offer.get("sku") or "")
        variant = clean_space(offer.get("variant") or "")
        key = (price, currency, sku) if sku else (price, currency, variant)
        score = len(variant)
        if offer.get("method") == "shopify_variant_json":
            score += 100
        if key not in best or score > best_score[key]:
            best[key] = offer
            best_score[key] = score
    out = list(best.values())
    if any(clean_space(offer.get("variant") or "") for offer in out):
        variant_prices = {(round(float(offer["price"]), 4), clean_space(offer.get("currency") or "")) for offer in out if clean_space(offer.get("variant") or "")}
        out = [
            offer
            for offer in out
            if clean_space(offer.get("variant") or "") or (round(float(offer["price"]), 4), clean_space(offer.get("currency") or "")) not in variant_prices
        ]
    if len(out) > 60:
        # Very large variant arrays are usually color permutations with identical pricing. Keep enough for coverage.
        out = out[:60]
    return out


def mass_candidates(text: str) -> list[tuple[float, str]]:
    text = clean_space(text).lower()
    num = r"(?:\d+(?:[.,]\d+)?|[.,]\d+)"
    found: list[tuple[float, str]] = []
    for m in re.finditer(rf"\b({num})\s*[x×]\s*({num})\s*(kg|g|lb|lbs|pounds?)\b", text, re.I):
        local = text[max(0, m.start() - 16) : m.end() + 16]
        if re.search(r"\b(moq|minimum order|min order)\b", local):
            continue
        count = float(m.group(1).replace(",", "."))
        amount = float(m.group(2).replace(",", "."))
        found.append((convert_mass(amount * count, m.group(3)), m.group(0)))
    for m in re.finditer(rf"(?<![\w.])({num})\s*(kg|kgs|kilograms?|g|grams?|lb|lbs|pounds?)\b", text, re.I):
        local = text[max(0, m.start() - 16) : m.end() + 16]
        if re.search(r"\b(moq|minimum order|min order)\b", local):
            continue
        amount = float(m.group(1).replace(",", "."))
        found.append((convert_mass(amount, m.group(2)), m.group(0)))
    return [(kg, src) for kg, src in found if 0.05 <= kg <= 25]


def convert_mass(amount: float, unit: str) -> float:
    unit = unit.lower()
    if unit.startswith("kg"):
        return amount
    if unit in {"g", "gram", "grams"}:
        return amount / 1000
    if unit.startswith("lb") or unit.startswith("pound"):
        return amount * 0.45359237
    return amount


def labeled_mass_from_soup(soup: BeautifulSoup) -> list[tuple[float, str]]:
    lines = [clean_space(line) for line in soup.get_text("\n", strip=True).splitlines()]
    out: list[tuple[float, str]] = []
    for line in lines:
        low = line.lower()
        if not re.search(r"(net weight|filament weight|spool weight|product weight|weight)", low):
            continue
        if re.search(r"(empty spool|gross|package|shipping|carton)", low):
            continue
        for kg, raw in mass_candidates(line):
            out.append((kg, f"labeled_page_text:{raw}"))
    return out


def infer_mass_kg(product: str, variant: str, html: str, url: str) -> tuple[float | None, str]:
    global SIDECAR_MASS_BY_URL
    if SIDECAR_MASS_BY_URL is None:
        SIDECAR_MASS_BY_URL = load_sidecar_mass_by_url()
    normalized_url = normalize_url(url)
    probes = [
        ("variant", variant),
        ("product", product),
        ("url", unquote(urlparse(url).path).replace("-", " ")),
    ]
    meta_desc = ""
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if meta and meta.get("content"):
        meta_desc = clean_space(meta["content"])
        probes.append(("description", meta_desc[:500]))
    for source, text in probes:
        candidates = mass_candidates(text)
        if candidates:
            # Product/variant titles often mention diameter and spool mass. The largest plausible mass is usually pack size.
            kg, raw = sorted(candidates, key=lambda x: x[0], reverse=True)[0]
            return round(kg, 6), f"{source}:{raw}"
    if normalized_url in SIDECAR_MASS_BY_URL:
        return SIDECAR_MASS_BY_URL[normalized_url]
    candidates = labeled_mass_from_soup(soup)
    if candidates:
        kg, raw = sorted(candidates, key=lambda x: x[0], reverse=True)[0]
        return round(kg, 6), raw
    return None, ""


def dedupe_price_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    seen = set()
    for row in rows:
        if not is_filament_price_row(row):
            continue
        key = (
            row.get("vendor"),
            row.get("url"),
            row.get("sku"),
            row.get("variant"),
            row.get("price"),
            row.get("currency"),
            row.get("mass_kg"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def product_url_price_rows(candidate: Candidate, run_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    shopify_rows = product_url_shopify_json_rows(candidate, run_rows)
    if shopify_rows:
        return shopify_rows
    try:
        response = fetch(candidate.url)
    except Exception as exc:
        log(run_rows, candidate.vendor, candidate.url, "fetch_product", "error", f"{type(exc).__name__}: {exc}")
        return []
    soup = soup_from_response(response)
    html = response.text
    title = title_from_soup(soup, response.url)
    default_currency = VENDOR_DEFAULT_CURRENCY.get(candidate.vendor, "") or currency_from_html(html, soup)
    offers = []
    offers.extend(offer_rows_from_jsonld(soup))
    offers.extend(shopify_variant_rows(html))
    offers.extend(meta_offer_rows(soup))
    if not offers and candidate.vendor == "Prusa Polymers":
        offers.extend(visible_price_rows(soup))
    offers = dedupe_offers(offers, default_currency)
    rows: list[dict[str, object]] = []
    for offer in offers:
        product_name = clean_space(offer.get("product_name") or title or candidate.hint_product)
        variant = clean_space(offer.get("variant") or "")
        mass, mass_source = infer_mass_kg(product_name, variant, html, response.url)
        price = float(offer["price"])
        price_per_kg = round(price / mass, 4) if mass else None
        rows.append(
            {
                "scraped_at": SCRAPED_AT,
                "vendor": candidate.vendor,
                "product": product_name,
                "variant": variant,
                "sku": clean_space(offer.get("sku") or ""),
                "url": normalize_url(response.url),
                "price": round(price, 4),
                "currency": clean_space(offer.get("currency") or default_currency),
                "mass_kg": mass,
                "mass_source": mass_source,
                "price_per_kg": price_per_kg,
                "availability": clean_space(offer.get("availability") or ""),
                "price_source": clean_space(offer.get("method") or ""),
                "candidate_source": candidate.source,
            }
        )
    status = "priced" if rows else "no_price"
    detail = f"{len(rows)} offers; title={title[:120]}"
    log(run_rows, candidate.vendor, candidate.url, "fetch_product", status, detail)
    time.sleep(0.12)
    return rows


def product_url_shopify_json_rows(candidate: Candidate, run_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    endpoint = shopify_product_json_url(candidate.url)
    if not endpoint:
        return []
    try:
        response = fetch(endpoint)
    except Exception:
        return []
    content_type = response.headers.get("content-type", "")
    if "json" not in content_type and "javascript" not in content_type:
        return []
    try:
        data = response.json()
    except Exception:
        return []
    product_name = clean_space(data.get("title") or candidate.hint_product)
    description_html = str(data.get("description") or "")
    variants = data.get("variants") if isinstance(data.get("variants"), list) else []
    rows: list[dict[str, object]] = []
    currency = VENDOR_DEFAULT_CURRENCY.get(candidate.vendor, "")
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        raw_price = variant.get("price")
        if raw_price is None:
            continue
        try:
            price = float(raw_price) / 100 if float(raw_price) > 200 else float(raw_price)
        except Exception:
            continue
        if not (0 < price < 10000):
            continue
        variant_name = clean_space(variant.get("name") or variant.get("public_title") or variant.get("title") or "")
        sku = clean_space(variant.get("sku") or "")
        mass, mass_source = infer_mass_kg(product_name, variant_name, description_html, candidate.url)
        rows.append(
            {
                "scraped_at": SCRAPED_AT,
                "vendor": candidate.vendor,
                "product": product_name,
                "variant": variant_name,
                "sku": sku,
                "url": normalize_url(candidate.url),
                "price": round(price, 4),
                "currency": currency,
                "mass_kg": mass,
                "mass_source": mass_source,
                "price_per_kg": round(price / mass, 4) if mass else None,
                "availability": "InStock" if variant.get("available") else "OutOfStock",
                "price_source": "shopify_product_js",
                "candidate_source": candidate.source,
            }
        )
    if rows:
        log(run_rows, candidate.vendor, candidate.url, "fetch_product_js", "priced", f"{len(rows)} variants; title={product_name[:120]}")
        time.sleep(0.05)
    return rows


def write_outputs(rows: list[dict[str, object]], run_rows: list[dict[str, str]], candidates: list[Candidate]) -> None:
    rows = dedupe_price_rows(rows)
    currencies = {clean_space(row.get("currency") or "") for row in rows if row.get("currency")}
    exchange_rates = fetch_usd_exchange_rates(currencies)
    rows = add_usd_conversions(rows, exchange_rates)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scraped_at",
        "vendor",
        "product",
        "variant",
        "sku",
        "url",
        "price",
        "currency",
        "mass_kg",
        "mass_source",
        "price_per_kg",
        "price_usd",
        "price_per_kg_usd",
        "exchange_rate_to_usd",
        "exchange_rate_date",
        "exchange_rate_source",
        "availability",
        "price_source",
        "candidate_source",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with RUN_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "vendor", "url", "action", "status", "detail"])
        writer.writeheader()
        writer.writerows(run_rows)
    by_vendor: dict[str, dict[str, object]] = {}
    for vendor in sorted({c.vendor for c in candidates} | {str(row["vendor"]) for row in rows}):
        vendor_rows = [row for row in rows if row["vendor"] == vendor]
        by_vendor[vendor] = {
            "candidate_urls": len({c.url for c in candidates if c.vendor == vendor}),
            "priced_rows": len(vendor_rows),
            "priced_products": len({row["url"] for row in vendor_rows}),
            "with_mass": sum(1 for row in vendor_rows if row.get("mass_kg")),
            "with_price_per_kg": sum(1 for row in vendor_rows if row.get("price_per_kg") is not None),
            "with_price_per_kg_usd": sum(1 for row in vendor_rows if row.get("price_per_kg_usd") is not None),
            "currencies": sorted({row.get("currency") for row in vendor_rows if row.get("currency")}),
        }
    payload = {
        "generated_at": SCRAPED_AT,
        "note": "Current public page price scrape. Prices exclude shipping, tax, and member pricing. Non-USD prices are converted with the listed reference exchange rates.",
        "exchange_rates_to_usd": exchange_rates,
        "summary": {
            "candidate_urls": len(candidates),
            "priced_rows": len(rows),
            "priced_products": len({row["url"] for row in rows}),
            "rows_with_mass": sum(1 for row in rows if row.get("mass_kg")),
            "rows_with_price_per_kg": sum(1 for row in rows if row.get("price_per_kg") is not None),
            "rows_with_price_per_kg_usd": sum(1 for row in rows if row.get("price_per_kg_usd") is not None),
            "vendors": by_vendor,
            "run_statuses": dict(Counter(f"{row['action']}:{row['status']}" for row in run_rows)),
        },
        "prices": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    run_rows: list[dict[str, str]] = []
    candidates = discover_candidates(run_rows)
    rows: list[dict[str, object]] = []
    for idx, candidate in enumerate(candidates, start=1):
        rows.extend(product_url_price_rows(candidate, run_rows))
        if idx % 25 == 0:
            print(f"processed {idx}/{len(candidates)} candidates; priced_rows={len(rows)}", flush=True)
        if idx % 50 == 0:
            write_outputs(rows, run_rows, candidates)
    write_outputs(rows, run_rows, candidates)
    summary = json.loads(OUT_JSON.read_text(encoding="utf-8"))["summary"]
    print(json.dumps({"json": str(OUT_JSON), "csv": str(OUT_CSV), "run": str(RUN_CSV), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
