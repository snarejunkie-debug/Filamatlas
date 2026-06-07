from __future__ import annotations

import csv
import json
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any

import fitz

try:
    import pdfplumber
except Exception:  # pragma: no cover
    pdfplumber = None


ROOT = Path(__file__).resolve().parents[1]
DATASHEET_ROOT = ROOT / "filament_datasheets"
ANALYSIS_DIR = ROOT / "analysis"
WEB_DATA_DIR = ROOT / "web" / "data"
DB_PATH = ANALYSIS_DIR / "filament_materials.sqlite"
JSON_PATH = WEB_DATA_DIR / "materials.json"
CSV_PATH = ANALYSIS_DIR / "material_properties_long.csv"
TAG_REPORT_PATH = ANALYSIS_DIR / "property_tag_study.md"
OCR_TEXT_OVERRIDES_PATH = DATASHEET_ROOT / "_manifest" / "ocr_text_overrides.json"
HTML_SPECS_PATH = DATASHEET_ROOT / "_manifest" / "html_material_specs.json"
AUDIT_JSON_PATH = ANALYSIS_DIR / "material_database_audit.json"
AUDIT_MD_PATH = ANALYSIS_DIR / "material_database_audit.md"


@dataclass(frozen=True)
class PropertyDef:
    key: str
    label: str
    category: str
    canonical_unit: str
    patterns: tuple[str, ...]
    compatible_units: tuple[str, ...]
    radar: bool = False
    higher_is_better: bool = True


PROPERTY_DEFS: list[PropertyDef] = [
    PropertyDef("diameter", "Filament diameter", "Filament specs", "mm", (r"diameter",), ("mm",)),
    PropertyDef("diameter_tolerance", "Diameter tolerance", "Filament specs", "mm", (r"diameter tolerance", r"tolerance"), ("mm",)),
    PropertyDef("roundness_deviation", "Roundness deviation", "Filament specs", "mm", (r"roundness",), ("mm",)),
    PropertyDef("net_weight", "Net filament weight", "Filament specs", "kg", (r"net filament weight", r"net weight"), ("kg", "g")),
    PropertyDef("filament_length", "Filament length", "Filament specs", "m", (r"filament length",), ("m",)),
    PropertyDef("nozzle_temperature", "Nozzle / extruder temperature", "Print settings", "degC", (r"nozzle temperature", r"extruder temperature", r"extrusion temp", r"print temperature", r"suggested print temperature"), ("degC", "degF")),
    PropertyDef("bed_temperature", "Bed / build plate temperature", "Print settings", "degC", (r"bed temperature", r"\bbed temp\b", r"build plate temperature", r"build plate temp", r"build platform temperature", r"heatbed temperature", r"suggested bed temperature"), ("degC", "degF")),
    PropertyDef("chamber_temperature", "Chamber temperature", "Print settings", "degC", (r"chamber temperature", r"chamber temp"), ("degC", "degF")),
    PropertyDef("drying_temperature", "Drying temperature", "Print settings", "degC", (r"drying", r"drying temp", r"drying temperature"), ("degC", "degF")),
    PropertyDef("annealing_temperature", "Annealing temperature", "Print settings", "degC", (r"annealing", r"annealing temp", r"annealing temperature"), ("degC", "degF")),
    PropertyDef("print_speed", "Print speed", "Print settings", "mm/s", (r"print speed", r"printing speed"), ("mm/s",)),
    PropertyDef("max_volumetric_speed", "Max volumetric speed", "Print settings", "mm3/s", (r"volumetric speed",), ("mm3/s",)),
    PropertyDef("density", "Density / specific gravity", "Physical", "g/cm3", (r"density", r"specific gravity"), ("g/cm3", "g/cc", "kg/m3"), True, False),
    PropertyDef("melt_flow_index", "Melt flow index / MFR", "Physical", "g/10min", (r"melt flow index", r"melt index", r"mfr", r"melt mass-flow rate"), ("g/10min",)),
    PropertyDef("melt_volume_rate", "Melt volume rate / MVR", "Physical", "cm3/10min", (r"mvr", r"melt volume"), ("cm3/10min",)),
    PropertyDef("water_absorption", "Water / moisture absorption", "Physical", "%", (r"water absorption", r"moisture absorption", r"saturated water absorption", r"equilibrium water absorption"), ("%",)),
    PropertyDef("shrinkage", "Shrinkage", "Physical", "%", (r"shrinkage",), ("%",)),
    PropertyDef("light_transmission", "Light transmission", "Physical", "%", (r"light transmission",), ("%",)),
    PropertyDef("tensile_strength", "Tensile strength / stress", "Mechanical", "MPa", (r"tensile .*strength", r"tensile .*stress", r"tensile yield strength"), ("MPa", "GPa", "kPa", "Pa", "psi", "ksi"), True),
    PropertyDef("tensile_modulus", "Tensile / Young's modulus", "Mechanical", "MPa", (r"young.?s modulus", r"tensile modulus"), ("MPa", "GPa", "kPa", "Pa", "psi", "ksi"), True),
    PropertyDef("elongation", "Elongation / strain", "Mechanical", "%", (r"elongation", r"breaking elongation", r"flexural strain"), ("%",), True),
    PropertyDef("flexural_strength", "Flexural / bending strength", "Mechanical", "MPa", (r"flexural strength", r"bending strength"), ("MPa", "GPa", "kPa", "Pa", "psi", "ksi"), True),
    PropertyDef("flexural_modulus", "Flexural / bending modulus", "Mechanical", "MPa", (r"flexural modulus", r"bending modulus"), ("MPa", "GPa", "kPa", "Pa", "psi", "ksi"), True),
    PropertyDef("impact_charpy", "Charpy impact strength", "Mechanical", "kJ/m2", (r"charpy.*impact", r"impact strength charpy"), ("kJ/m2", "J/m2"), True),
    PropertyDef("impact_izod", "Izod impact strength", "Mechanical", "J/m", (r"izod.*impact", r"notched izod"), ("J/m", "kJ/m2", "J/m2"), False),
    PropertyDef("impact_izod_area", "Izod impact strength (area-normalized)", "Mechanical", "kJ/m2", (), ("kJ/m2", "J/m2"), False),
    PropertyDef("impact_strength", "Impact strength", "Mechanical", "kJ/m2", (r"impact strength",), ("kJ/m2", "J/m2"), True),
    PropertyDef("hardness_shore_d", "Hardness Shore D", "Mechanical", "Shore D", (r"shore d", r"hardness"), ("Shore D",)),
    PropertyDef("hardness_shore_a", "Hardness Shore A", "Mechanical", "Shore A", (r"shore a",), ("Shore A",)),
    PropertyDef("hdt", "Heat deflection / distortion temperature", "Thermal", "degC", (r"heat deflection", r"heat distortion", r"hdt", r"thermal deformation"), ("degC", "degF"), True),
    PropertyDef("vicat", "Vicat softening temperature", "Thermal", "degC", (r"vicat", r"vicar softening"), ("degC", "degF"), True),
    PropertyDef("glass_transition", "Glass transition temperature", "Thermal", "degC", (r"glass transition", r"\btg\b"), ("degC", "degF"), True),
    PropertyDef("melting_temperature", "Melting temperature", "Thermal", "degC", (r"melting temperature", r"\btm\b"), ("degC", "degF"), True),
    PropertyDef("crystallization_temperature", "Crystallization temperature", "Thermal", "degC", (r"crystallization temperature",), ("degC", "degF")),
    PropertyDef("decomposition_temperature", "Decomposition temperature", "Thermal", "degC", (r"decomposition temperature",), ("degC", "degF")),
    PropertyDef("continuous_service_temperature", "Continuous service temperature", "Thermal", "degC", (r"continuous service temperature",), ("degC", "degF")),
    PropertyDef("max_short_term_temperature", "Maximum short-term use temperature", "Thermal", "degC", (r"maximum.*short.*temperature", r"maximum.*use temperature"), ("degC", "degF")),
    PropertyDef("surface_resistance", "Surface resistance / resistivity", "Electrical", "ohm/sq", (r"surface resistance", r"surface resistivity"), ("ohm/sq", "ohm")),
    PropertyDef("insulation_resistance", "Insulation resistance", "Electrical", "ohm", (r"insulation resistance",), ("ohm",)),
    PropertyDef("flame_retardancy", "Flame retardancy", "Safety / chemical", "rating", (r"flame retardancy", r"flammability"), ("rating",)),
    PropertyDef("chemical_resistance", "Chemical resistance", "Safety / chemical", "rating", (r"chemical resistance", r"effect of weak acids", r"effect of strong acids", r"resistance to acid", r"resistance to alkali", r"resistance to organic solvent", r"effect of oils"), ("rating",)),
    PropertyDef("interlayer_adhesion", "Interlayer adhesion", "Mechanical", "MPa", (r"interlayer adhesion",), ("MPa", "GPa", "kPa", "Pa", "psi", "ksi"), True),
    PropertyDef("deflection_at_flexural_strength", "Deflection at flexural strength", "Mechanical", "mm", (r"deflection at flexural",), ("mm",)),
]

PROP_BY_KEY = {p.key: p for p in PROPERTY_DEFS}


SKIP_NAME_PARTS = (
    "logo",
    "catalog",
    "polityka",
    "privacy",
    "iso_9001",
    "cert_2026",
    ".ds_store",
)

NON_EN_LANGUAGE_MARKERS = (
    "_PL.pdf",
    "_JP.pdf",
    "_IT.pdf",
    "_FR.pdf",
    "_ES.pdf",
    "_DE.pdf",
    "_CZ.pdf",
    "_CS.pdf",
    "2022_PL.pdf",
    "2022_JP.pdf",
    "2022_IT.pdf",
    "2022_FR.pdf",
    "2022_ES.pdf",
    "2022_DE.pdf",
    "2022_CZ.pdf",
)


def clean_text(text: str) -> str:
    text = text.replace("\u2122\ufe0f", "TM").replace("\u2122", "TM")
    text = text.replace("\u00ae", "").replace("\u00b5", "u")
    text = text.replace("\u00b1", "+/-").replace("\u2264", "<=").replace("\u2265", ">=")
    text = text.replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u223c", "~").replace("\uff5e", "~")
    text = text.replace("\uff0c", ",").replace("\uff08", "(").replace("\uff09", ")")
    text = text.replace("\u2103", "°C").replace("\u02da", "°")
    text = text.replace("\u00c2\u00b0", "\u00b0").replace("\u00c2\u00b2", "2").replace("\u00c2\u00b3", "3")
    text = re.sub(r"(?<=\d)\s*~\s*(?=\d)", "-", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    return text


def compact_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", clean_text(text)).strip()


def read_pdf(path: Path, extract_tables: bool = False) -> tuple[str, list[str], int, str | None]:
    texts: list[str] = []
    row_texts: list[str] = []
    pages = 0
    try:
        with fitz.open(str(path)) as doc:
            pages = len(doc)
            for page in doc:
                texts.append(page.get_text("text"))
    except Exception as exc:
        return "", [], 0, f"pdf_open_failed:{type(exc).__name__}:{exc}"

    if extract_tables and pdfplumber:
        try:
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    for table in page.extract_tables() or []:
                        for row in table:
                            cells = [compact_spaces(c or "") for c in row if compact_spaces(c or "")]
                            if cells:
                                row_texts.append(" | ".join(cells))
        except Exception as exc:
            row_texts.append(f"TABLE_EXTRACTION_ERROR {type(exc).__name__}: {exc}")

    return clean_text("\n".join(texts)), row_texts, pages, None


def load_ocr_text_overrides() -> dict[str, Any]:
    if not OCR_TEXT_OVERRIDES_PATH.exists():
        return {}
    try:
        data = json.loads(OCR_TEXT_OVERRIDES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    entries = data.get("entries", data)
    return entries if isinstance(entries, dict) else {}


OCR_TEXT_OVERRIDES = load_ocr_text_overrides()
AUDIT_REJECTIONS: list[dict[str, Any]] = []
AUDIT_REJECTION_KEYS: set[tuple[str, str, str, str, str]] = set()


def record_rejection(source: dict[str, Any] | None, prop: PropertyDef, raw_value: str, reason: str, ctx: str) -> None:
    source = source or {}
    key = (
        str(source.get("source_file") or source.get("source_url") or ""),
        str(source.get("product") or ""),
        prop.key,
        str(raw_value),
        reason,
    )
    if key in AUDIT_REJECTION_KEYS:
        return
    AUDIT_REJECTION_KEYS.add(key)
    AUDIT_REJECTIONS.append(
        {
            "supplier": source.get("supplier"),
            "product": source.get("product"),
            "source_type": source.get("source_type"),
            "source_file": source.get("source_file") or source.get("source_url"),
            "property_key": prop.key,
            "property_label": prop.label,
            "raw_value": raw_value,
            "reason": reason,
            "source_context": compact_spaces(ctx)[:500],
        }
    )


def ocr_text_override(path: Path) -> tuple[str, list[str], str] | None:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        rel = path.as_posix()
    entry = OCR_TEXT_OVERRIDES.get(rel)
    if isinstance(entry, str):
        return entry, [], "ocr_text_override"
    if not isinstance(entry, dict):
        return None
    text = str(entry.get("text") or "")
    rows = entry.get("rows") or []
    if not isinstance(rows, list):
        rows = []
    clean_rows = [compact_spaces(str(row)) for row in rows if compact_spaces(str(row))]
    mode = compact_spaces(str(entry.get("mode") or "ocr_text_override"))
    if not text and not clean_rows:
        return None
    return text, clean_rows, mode


def append_quality_flag(existing: str | None, flag: str) -> str:
    bits = [bit for bit in (existing or "").split(";") if bit]
    if flag not in bits:
        bits.append(flag)
    return ";".join(bits)


def should_skip_pdf(path: Path) -> tuple[bool, str]:
    lower = path.name.lower()
    if any(part in lower for part in SKIP_NAME_PARTS):
        return True, "non_material_or_auxiliary"
    if any(path.name.endswith(marker) for marker in NON_EN_LANGUAGE_MARKERS):
        if not path.name.endswith("_EN.pdf"):
            return True, "non_english_duplicate"
    return False, ""


def supplier_from_path(path: Path) -> str:
    try:
        return path.relative_to(DATASHEET_ROOT).parts[0]
    except Exception:
        return "Unknown"


def strip_product_from_filename(path: Path, supplier: str) -> str:
    name = path.stem
    name = re.sub(r"\s*-\s*technical_datasheet(?:\s*\(\d+\))?$", "", name, flags=re.I)
    name = re.sub(r"\s*-\s*technical_datasheet.*$", "", name, flags=re.I)
    name = re.sub(rf"^{re.escape(supplier)}\s*-\s*", "", name, flags=re.I)
    name = re.sub(r"^3DXTech\s*-\s*(?:3DXTech|Triton3D) Technical and Safety Data Sheets\s*-\s*", "", name, flags=re.I)
    name = re.sub(r"^Prusa Polymers\s*-\s*", "", name, flags=re.I)
    name = name.replace("_", " ")
    name = re.sub(r"\bTDS\b.*$", "", name, flags=re.I)
    name = re.sub(r"\bv\d+(?:\.\d+)?\b", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name).strip(" -_")
    return name or path.stem


def extract_text_product(text: str, fallback: str) -> str:
    patterns = [
        r"Technical Data Sheet:\s*([^\n]+)",
        r"Trade Name\s*\n\s*([^\n]+)",
        r"TECHNICAL DATA SHEET\s*-\s*([^\n]+)",
        r"Technical datasheet\s*\n\s*([^\n]+)",
        r"Bambu Filament\s*\nTechnical Data Sheet[^\n]*\n\s*([^\n]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            product = compact_spaces(m.group(1))
            product = re.sub(r"\s+3D Printing Filament$", "", product, flags=re.I)
            if len(product) >= 2 and "certificate" not in product.lower():
                return product
    return fallback


def classify_material(product: str) -> tuple[str, str, list[str]]:
    up = product.upper().replace("™", "").replace("®", "")
    modifiers: list[str] = []
    if "COLORFABB_XT" in up or "COLORFABB XT" in up:
        return "CPE", "colorFabb_XT", modifiers
    if "COLORFABB_HT" in up or "COLORFABB HT" in up:
        return "CPE", "colorFabb_HT", modifiers
    if "XT-CF20" in up or "XT CF20" in up:
        return "CPE", "XT-CF20", ["Carbon fiber"]
    tokens = [
        "PLA-CF", "PETG-CF", "PA6-CF", "PA12-CF", "PA612-CF", "PC-ABS", "PC ABS",
        "PCASA", "PC-ASA", "ABS-GF", "ASA-CF", "PET-CF", "PPA-CF", "PPS-CF",
        "TPU", "PETG", "PCTG", "PLA", "ABS", "ASA", "HIPS", "PAHT", "PA6",
        "PA12", "PA11", "NYLON", "PA", "PC", "PEEK", "PEKK", "PEI", "ULTEM", "PPSU",
        "PPS", "PSU", "PVDF", "PVA", "PVB", "PHA", "PP", "CPE",
    ]
    full = "Unknown"
    for token in tokens:
        if token in up:
            full = token.replace("NYLON", "PA")
            break
    if full in {"PLA-CF", "PETG-CF", "PA6-CF", "PA12-CF", "PA612-CF", "PC-ABS", "PC ABS", "PCASA", "PC-ASA"}:
        base = full.split("-")[0].replace("PCASA", "PC").replace("PC ABS", "PC")
    elif full in {"ABS-GF", "ASA-CF", "PET-CF", "PPA-CF", "PPS-CF"}:
        base = full.split("-")[0]
    elif full == "ULTEM":
        base = "PEI"
    else:
        base = full

    modifier_words = {
        "MATTE": "Matte",
        "BASIC": "Basic",
        "SILK": "Silk",
        "WOOD": "Wood",
        "STONEFILL": "Stone",
        "BRONZEFILL": "Metal",
        "COPPERFILL": "Metal",
        "STEELFILL": "Metal",
        "LIGHT WEIGHT": "Lightweight",
        "CF": "Carbon fiber",
        "CARBON": "Carbon fiber",
        "GF": "Glass fiber",
        "GLASS": "Glass fiber",
        "ESD": "ESD",
        "AERO": "Aero",
        "GLOW": "Glow",
        "MARBLE": "Marble",
        "METAL": "Metal",
        "RECYCLED": "Recycled",
        "TOUGH": "Tough",
        "HIGH SPEED": "High speed",
        "HS": "High speed",
        "PRO": "Pro",
        "MAX": "Max",
        "FLEX": "Flexible",
        "SUPPORT": "Support",
        "TRANSLUCENT": "Translucent",
        "TRANSPARENT": "Transparent",
        "FIRE": "Flame retardant",
        "FR": "Flame retardant",
    }
    for needle, tag in modifier_words.items():
        if needle in up and tag not in modifiers:
            modifiers.append(tag)
    if full != "Unknown" and ("CF" in full or "CARBON" in up) and "Carbon fiber" not in modifiers:
        modifiers.append("Carbon fiber")
    if full != "Unknown" and ("GF" in full or "GLASS" in up) and "Glass fiber" not in modifiers:
        modifiers.append("Glass fiber")

    signature_modifiers = [
        m
        for m in modifiers
        if m
        in {
            "Matte",
            "Basic",
            "Silk",
            "Wood",
            "Carbon fiber",
            "Glass fiber",
            "ESD",
            "Aero",
            "Glow",
            "Marble",
            "Metal",
            "Recycled",
            "Tough",
            "High speed",
            "Pro",
            "Support",
            "Translucent",
            "Transparent",
            "Flame retardant",
            "Flexible",
        }
    ]
    family = full
    for mod in signature_modifiers:
        if mod == "Carbon fiber" and ("CF" in family or "CARBON" in family):
            continue
        if mod == "Glass fiber" and ("GF" in family or "GLASS" in family):
            continue
        if mod.upper() not in family.upper():
            family = f"{family} {mod}"

    return base, family, modifiers


NUM = r"[-+]?\d+(?:[.,]\d+)?"
VALUE_RE = re.compile(
    rf"(?P<prefix>[<>~])?\s*(?P<a>{NUM})(?:\s*(?:±|\+/-)\s*(?P<pm>{NUM}))?(?:\s*(?:-|to|–)\s*(?P<b>{NUM}))?",
    re.I,
)

PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "diameter": (0.5, 5.0),
    "diameter_tolerance": (0, 0.5),
    "roundness_deviation": (0, 0.5),
    "net_weight": (0.05, 20),
    "filament_length": (1, 5000),
    "nozzle_temperature": (100, 550),
    "bed_temperature": (0, 170),
    "chamber_temperature": (0, 180),
    "drying_temperature": (20, 220),
    "annealing_temperature": (20, 300),
    "print_speed": (1, 1000),
    "max_volumetric_speed": (0.1, 100),
    "density": (0.5, 5),
    "melt_flow_index": (0, 500),
    "melt_volume_rate": (0, 500),
    "water_absorption": (0, 100),
    "shrinkage": (0, 100),
    "light_transmission": (0, 100),
    "tensile_strength": (0, 300),
    "tensile_modulus": (0, 100000),
    "elongation": (0, 1500),
    "flexural_strength": (0, 500),
    "flexural_modulus": (0, 100000),
    "impact_charpy": (0, 500),
    "impact_izod": (0, 10000),
    "impact_izod_area": (0, 500),
    "impact_strength": (0, 500),
    "hardness_shore_d": (20, 120),
    "hardness_shore_a": (20, 120),
    "hdt": (20, 450),
    "vicat": (20, 450),
    "glass_transition": (-100, 450),
    "melting_temperature": (20, 500),
    "crystallization_temperature": (20, 450),
    "decomposition_temperature": (0, 1000),
    "continuous_service_temperature": (-100, 500),
    "max_short_term_temperature": (-100, 500),
    "interlayer_adhesion": (0, 1000),
    "deflection_at_flexural_strength": (0, 100),
}

AREA_IMPACT_UNITS = {"kJ/m2", "J/m2"}
LINEAR_IMPACT_UNITS = {"J/m", "ft-lb/in"}
FT_LBF_PER_IN_TO_J_PER_M = 1.3558179483314004 / 0.0254


def has_ft_lbf_per_in(text: str) -> bool:
    compact = text.lower().replace(" ", "").replace("\u00b7", "-").replace("*", "-")
    return bool(re.search(r"ft[-.]?(?:lb|lbf)/in", compact) or re.search(r"ft(?:lb|lbf)/in", compact))


def detect_unit(text: str, prop: PropertyDef) -> str | None:
    t = text.replace("³", "3").replace("²", "2").replace(" ", "")
    tl = t.lower()
    if prop.key in {"impact_charpy", "impact_izod", "impact_izod_area", "impact_strength"} and has_ft_lbf_per_in(text):
        return "ft-lb/in"
    if prop.canonical_unit == "degC":
        if "\u00b0f" in tl:
            return "degF"
        if "\u00b0c" in tl:
            return "degC"
        if "°f" in tl or "\u2109" in text or re.search(r"\bf\b", text, re.I):
            return "degF"
        if "°c" in tl or "\u2103" in text or "degc" in tl or re.search(r"\d\s*c\b", text, re.I):
            return "degC"
        return "degC"
    if prop.canonical_unit == "MPa":
        if "gpa" in tl:
            return "GPa"
        if "mpa" in tl:
            return "MPa"
        if "kpa" in tl:
            return "kPa"
        if re.search(r"\bpa\b", tl):
            return "Pa"
        if "ksi" in tl:
            return "ksi"
        if "psi" in tl:
            return "psi"
        return "MPa"
    if prop.canonical_unit == "g/cm3":
        if "kg/m3" in tl or "kg/m³" in tl:
            return "kg/m3"
        if "g/cc" in tl:
            return "g/cc"
        return "g/cm3"
    if prop.canonical_unit == "g/10min":
        return "g/10min"
    if prop.canonical_unit == "cm3/10min":
        return "cm3/10min"
    if prop.canonical_unit == "kJ/m2":
        if "j/m2" in tl and "kj/m2" not in tl:
            return "J/m2"
        if "j/m²" in tl and "kj/m²" not in tl:
            return "J/m2"
        if "j/m" in tl and "kj/m" not in tl:
            return "J/m"
        return "kJ/m2"
    if prop.canonical_unit == "J/m":
        if "kj/m2" in tl or "kj/m²" in tl:
            return "kJ/m2"
        if "j/m2" in tl or "j/m²" in tl:
            return "J/m2"
        return "J/m"
    if prop.canonical_unit == "%":
        return "%"
    if prop.canonical_unit == "kg":
        return "g" if re.search(r"\d\s*g\b", text, re.I) and not re.search(r"\d\s*kg\b", text, re.I) else "kg"
    if prop.canonical_unit == "mm3/s":
        return "mm3/s"
    if prop.canonical_unit in {"mm", "m", "mm/s"}:
        return prop.canonical_unit
    if prop.canonical_unit in {"Shore D", "Shore A", "rating", "ohm", "ohm/sq"}:
        return prop.canonical_unit
    return prop.canonical_unit


def convert_value(value: float, from_unit: str, to_unit: str) -> float | None:
    if from_unit == to_unit:
        return value
    if to_unit == "degC" and from_unit == "degF":
        return (value - 32) * 5 / 9
    if to_unit == "MPa":
        return {
            "GPa": value * 1000,
            "kPa": value / 1000,
            "Pa": value / 1_000_000,
            "psi": value * 0.006894757,
            "ksi": value * 6.894757,
            "MPa": value,
        }.get(from_unit)
    if to_unit == "g/cm3":
        return {
            "kg/m3": value / 1000,
            "g/cc": value,
            "g/cm3": value,
        }.get(from_unit)
    if to_unit == "kg" and from_unit == "g":
        return value / 1000
    if to_unit == "kJ/m2" and from_unit == "J/m2":
        return value / 1000
    if to_unit == "J/m" and from_unit == "ft-lb/in":
        return value * FT_LBF_PER_IN_TO_J_PER_M
    return None


def parse_numeric(raw: str, unit_raw: str, unit_canonical: str) -> tuple[float | None, float | None, float | None, str]:
    m = VALUE_RE.search(raw.replace(",", "."))
    if not m:
        return None, None, None, "non_numeric"
    a = float(m.group("a"))
    b = float(m.group("b")) if m.group("b") else None
    pm = float(m.group("pm")) if m.group("pm") else None
    flags = []
    if m.group("prefix"):
        flags.append(f"inequality:{m.group('prefix')}")
    if pm is not None:
        lo, hi = a - pm, a + pm
        nominal = a
    elif b is not None:
        lo, hi = min(a, b), max(a, b)
        nominal = (lo + hi) / 2
    else:
        lo = hi = nominal = a
    converted = [convert_value(v, unit_raw, unit_canonical) for v in (lo, hi, nominal)]
    if any(v is None for v in converted):
        flags.append("unit_not_converted")
        return lo, hi, nominal, ";".join(flags)
    if unit_raw != unit_canonical:
        flags.append(f"unit_converted:{unit_raw}->{unit_canonical}")
    return converted[0], converted[1], converted[2], ";".join(flags)


def is_method_cell(cell: str) -> bool:
    return bool(re.search(r"^\s*(ISO|ASTM|GB/T|IEC|DIN|UL)\b", cell, re.I))


def cell_has_test_condition_only(cell: str, prop: PropertyDef) -> bool:
    c = cell.lower()
    if prop.canonical_unit == "degC" and ("\u00b0c/min" in c or "mpa" in c):
        return True
    if prop.canonical_unit == "degC" and ("/min" in c or "°c/min" in c):
        return True
    if prop.key in {"melt_flow_index", "melt_volume_rate"}:
        return False
    if "kg" in c and prop.canonical_unit not in {"kg", "g/10min", "cm3/10min"}:
        return True
    return False


def match_is_test_condition(match: re.Match[str], cell: str, prop: PropertyDef) -> bool:
    start, end = match.span()
    local = cell[max(0, start - 24) : min(len(cell), end + 32)].lower()
    before = cell[max(0, start - 8) : start].replace(" ", "")
    after = cell[end : min(len(cell), end + 8)].replace(" ", "").lower()
    if re.search(r"\b3\s*d\b|3d\s*(?:print|printing|\.com)", local):
        return True
    if match.group(0).strip().replace(",", ".") in {"10", "10.0"} and before.endswith("/") and after.startswith("min"):
        return True
    if re.search(r"\b(?:in\s*)?\d+(?:[.,]\d+)?\s*(?:h|hr|hrs|hour|hours)\b", local):
        return True
    if prop.canonical_unit == "degC" and re.search(r"\bmpa\b|/min|\d+(?:[.,]\d+)?\s*kg\b", local):
        return True
    if prop.key not in {"diameter", "diameter_tolerance", "roundness_deviation", "nozzle_temperature", "bed_temperature"}:
        if re.search(r"\b(nozzle|layer height|specimen|sample|length|width|diameter|infill)\b", local):
            return True
    return False


PROPERTY_LABEL_WORDS = (
    "diameter",
    "tolerance",
    "roundness",
    "weight",
    "length",
    "nozzle",
    "extruder",
    "extrusion",
    "bed",
    "plate",
    "chamber",
    "drying",
    "annealing",
    "speed",
    "density",
    "specific gravity",
    "mfr",
    "mvr",
    "melt flow",
    "water absorption",
    "moisture absorption",
    "tensile",
    "young",
    "elongation",
    "flexural",
    "bending",
    "impact",
    "charpy",
    "izod",
    "hardness",
    "shore",
    "heat deflection",
    "heat distortion",
    "hdt",
    "vicat",
    "glass transition",
    "melting",
    "surface resistance",
    "resistivity",
    "flammability",
    "chemical resistance",
)


def normalize_unit_text(text: str) -> str:
    t = clean_text(text).lower()
    t = t.replace(" ", "").replace("|", "")
    t = t.replace("\u00b2", "2").replace("\u00b3", "3")
    t = t.replace("Â²", "2").replace("Â³", "3")
    t = t.replace("\u00b0", "deg").replace("Â°", "deg")
    return t


def is_header_or_metadata_cell(cell: str) -> bool:
    c = compact_spaces(cell).lower().strip(":")
    if not c:
        return True
    return c in {
        "unit",
        "units",
        "typical value",
        "value",
        "method",
        "test method",
        "testing method",
        "standard",
        "property",
        "properties",
        "official_html_specs",
        "official_html_title",
    }


def is_unit_only_cell(cell: str) -> bool:
    c = normalize_unit_text(cell)
    return bool(
        re.fullmatch(
            r"[\[\(]?(degc|degf|c|f|mpa|gpa|kpa|pa|psi|ksi|g/cm3|g/cc|kg/m3|g/10min|cm3/10min|mm3/s|mm/s|mm|m|kg|g|%|kj/m2|j/m2|j/m|ft-?lbf?/in|ohm|ohm/sq|shored|shorea)[\]\)]?",
            c,
            re.I,
        )
    )


def is_unit_exponent_capture(raw: str, local: str, prop: PropertyDef) -> bool:
    value = raw.strip().replace(",", ".")
    if value not in {"1", "2", "3"}:
        return False
    compact = normalize_unit_text(local)
    if value == "3" and re.search(r"(g/cm3|cm3|mm3|kg/m3|mm3/s)", compact):
        return True
    if value == "2" and re.search(r"(m2|mm2|cm2|j/m2|kj/m2)", compact):
        return True
    if re.search(r"\[%\]\(?[123]\)?|\([123]\)", compact) and prop.key not in {"diameter", "net_weight"}:
        return True
    return False


def cell_has_other_property_label(cell: str, prop: PropertyDef, pat: re.Pattern[str]) -> bool:
    c = cell.lower()
    if pat.search(cell):
        return False
    return any(word in c for word in PROPERTY_LABEL_WORDS)


def has_impact_unit_context(normalized_cell: str) -> bool:
    return bool(re.search(r"(kj/m2|j/m2|j/m(?!2)|ft-?lbf?/in)", normalized_cell))


def has_conflicting_explicit_unit(cell: str, prop: PropertyDef) -> bool:
    c = normalize_unit_text(cell)
    if prop.canonical_unit in {"mm", "m", "degC", "%", "kg"}:
        return False
    if prop.canonical_unit == "g/cm3":
        return bool(re.search(r"(mm|m\b|kg\b|g/10min|cm3/10min|mpa|kj/m2|j/m2|j/m)", c) and not re.search(r"(g/cm3|g/cc|kg/m3)", c))
    if prop.canonical_unit in {"kJ/m2", "J/m"}:
        return bool(
            re.search(r"(mm|m\b|g/cm3|g/cc|kg/m3|degc|mpa|gpa|kpa|psi|ksi)", c)
            and not has_impact_unit_context(c)
        )
    if prop.canonical_unit == "MPa":
        return bool(re.search(r"(g/cm3|degc|kj/m2|j/m2|j/m|mm/s|cm3/10min|g/10min)", c) and not re.search(r"(mpa|gpa|kpa|psi|ksi)", c))
    if prop.canonical_unit in {"g/10min", "cm3/10min"}:
        return bool(re.search(r"(g/cm3|mpa|degc|kj/m2|j/m2|mm/s)", c) and prop.canonical_unit not in c)
    return False


def candidate_raw_value(cell: str, prop: PropertyDef, pat: re.Pattern[str], label_cell: str = "") -> str | None:
    if is_header_or_metadata_cell(cell) or is_unit_only_cell(cell):
        return None
    if is_method_cell(cell) or cell_has_test_condition_only(cell, prop):
        return None
    if cell_has_other_property_label(cell, prop, pat):
        return None
    if has_conflicting_explicit_unit(cell, prop):
        return None
    normalized_cell = cell.replace(",", ".")
    label_match = pat.search(cell)
    label_end = label_match.end() if label_match else 0
    for match in VALUE_RE.finditer(normalized_cell):
        if label_match and match.start() < label_end:
            continue
        raw = match.group(0)
        local = f"{label_cell} {cell[max(0, match.start() - 24): min(len(cell), match.end() + 32)]}"
        if match_is_test_condition(match, normalized_cell, prop):
            continue
        if is_unit_exponent_capture(raw, local, prop):
            continue
        if has_conflicting_explicit_unit(local, prop):
            continue
        return raw
    return None


def audit_rejected_candidates(ctx: str, prop: PropertyDef, pat: re.Pattern[str], source: dict[str, Any] | None) -> None:
    if prop.canonical_unit == "rating":
        return
    for match in VALUE_RE.finditer(ctx.replace(",", ".")):
        raw = match.group(0)
        start, end = match.span()
        local = ctx[max(0, start - 32) : min(len(ctx), end + 40)]
        reason = None
        if is_unit_exponent_capture(raw, local, prop):
            reason = "unit_exponent_or_footnote"
        elif is_unit_only_cell(local):
            reason = "unit_only_cell"
        elif is_header_or_metadata_cell(local):
            reason = "header_or_metadata"
        elif has_conflicting_explicit_unit(local, prop):
            reason = "conflicting_explicit_unit"
        if reason:
            record_rejection(source, prop, raw, reason, ctx)


def choose_raw_value(ctx: str, prop: PropertyDef, pat: re.Pattern[str]) -> str | None:
    cells = [compact_spaces(c) for c in ctx.split("|")]
    label_index = None
    for idx, cell in enumerate(cells):
        if pat.search(cell):
            label_index = idx
            break
    if label_index is not None:
        label_cell = cells[label_index]
        raw = candidate_raw_value(label_cell, prop, pat, label_cell)
        if raw:
            return raw
        for cell in cells[label_index + 1 :]:
            raw = candidate_raw_value(cell, prop, pat, label_cell)
            if raw:
                return raw

    label_match = pat.search(ctx)
    search_part = ctx[label_match.end() :] if label_match else ctx
    candidates = []
    normalized_search_part = search_part.replace(",", ".")
    for m in VALUE_RE.finditer(normalized_search_part):
        start, end = m.span()
        before = search_part[max(0, start - 16) : start]
        after = search_part[end : min(len(search_part), end + 24)]
        local = before + m.group(0) + after
        if match_is_test_condition(m, normalized_search_part, prop):
            continue
        if re.search(r"(ISO|ASTM|GB/T|IEC|DIN|UL)\s*$", before, re.I):
            continue
        if is_header_or_metadata_cell(local) or is_unit_only_cell(local):
            continue
        if is_unit_exponent_capture(m.group(0), local, prop):
            continue
        if cell_has_other_property_label(local, prop, pat):
            continue
        if has_conflicting_explicit_unit(local, prop):
            continue
        if cell_has_test_condition_only(local, prop):
            continue
        score = 0
        if detect_unit(local, prop) == prop.canonical_unit:
            score += 2
        if prop.canonical_unit in {"MPa", "degC", "g/cm3", "kJ/m2", "J/m"} and re.search(r"(MPa|GPa|°C|\u2103|degC|\bC\b|g/cm|g/cc|kJ/m|J/m|ft[- ]?lb|ft[- ]?lbf|Shore)", local, re.I):
            score += 2
        score += 1 - (start / max(1, len(search_part)))
        candidates.append((score, m.group(0)))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return None


def is_plausible(prop_key: str, value: float | None) -> bool:
    if value is None or prop_key not in PLAUSIBLE_RANGES:
        return True
    lo, hi = PLAUSIBLE_RANGES[prop_key]
    return lo <= value <= hi


def property_patterns(prop: PropertyDef) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{p})" for p in prop.patterns), re.I)


def infer_orientation(text: str) -> str | None:
    t = text.upper()
    for val in ("X-Y", "XY", "YZ", "Z", "HORIZONTAL", "VERTICAL"):
        if re.search(rf"\b{re.escape(val)}\b", t):
            return val
    if "FLAT" in t:
        return "flat"
    if "SIDE" in t:
        return "side"
    if re.search(r"\bUP\b", t):
        return "up"
    return None


def infer_condition(text: str) -> str | None:
    tl = text.lower()
    bits = []
    patterns = (
        ("dry", r"\bdry\b"),
        ("wet", r"\bwet\b"),
        ("annealed", r"\bannealed\b"),
        ("dried", r"\bdried\b"),
        ("conditioned", r"\bconditioned\b"),
        ("unnotched", r"\bunnotched\b"),
        ("notched", r"(?<!un)\bnotched\b"),
        ("yield", r"\byield\b"),
        ("break", r"\bbreak\b"),
    )
    for word, pattern in patterns:
        if re.search(pattern, tl):
            bits.append(word)
    if "0.45" in tl or "0,45" in tl or "0.455" in tl:
        bits.append("0.45 MPa load")
    if "1.8" in tl or "1,8" in tl or "1.80" in tl:
        bits.append("1.8 MPa load")
    return ", ".join(dict.fromkeys(bits)) or None


def infer_method(text: str) -> str | None:
    m = re.search(r"\b(?:ISO|ASTM|GB/T|IEC|DIN|UL)\s*[-/]?\s*[A-Z]?\s*\d+(?:[-/]\d+)?(?:\s*/\s*[A-Z0-9]+)?", text, re.I)
    if m:
        return compact_spaces(m.group(0)).upper()
    for method in ("DSC", "TGA"):
        if re.search(rf"\b{method}\b", text, re.I):
            return method
    return None


def local_observation_context(ctx: str, pat: re.Pattern[str], raw_val: str | None) -> str:
    match = pat.search(ctx)
    if not match:
        return compact_spaces(ctx)[:500]
    end = match.end() + 220
    if raw_val:
        value_at = ctx.find(raw_val, match.end())
        if value_at >= 0:
            end = max(end, value_at + len(raw_val) + 120)
    return compact_spaces(ctx[match.start() : end])[:500]


def impact_unit_family(unit: str | None) -> str | None:
    if unit in AREA_IMPACT_UNITS:
        return "area"
    if unit in LINEAR_IMPACT_UNITS:
        return "linear"
    return None


def impact_method_family(text: str) -> str | None:
    if re.search(r"\bISO\s*[-/]?\s*179\b", text, re.I) or re.search(r"\bASTM\s*D\s*6110\b", text, re.I):
        return "charpy_area"
    if re.search(r"\bISO\s*[-/]?\s*180\b", text, re.I):
        return "iso_izod_area"
    if re.search(r"\bASTM\s*D\s*(?:256|4812)\b", text, re.I):
        return "astm_izod_linear"
    return None


def resolve_impact_property(prop: PropertyDef, ctx: str, unit_raw: str | None) -> tuple[PropertyDef, list[str]]:
    if prop.key not in {"impact_charpy", "impact_izod", "impact_strength"}:
        return prop, []
    method_family = impact_method_family(ctx)
    unit_family = impact_unit_family(unit_raw)
    flags: list[str] = []

    if prop.key == "impact_izod":
        if method_family == "charpy_area":
            flags.append("source_label_mismatch:izod_label_iso179")
            return PROP_BY_KEY["impact_charpy"], flags
        if method_family == "iso_izod_area" or unit_family == "area":
            flags.append("impact_area_normalized")
            if method_family == "astm_izod_linear":
                flags.append("impact_method_unit_mismatch:astm_linear_method_area_unit")
            return PROP_BY_KEY["impact_izod_area"], flags
        return prop, flags

    if prop.key == "impact_strength":
        if method_family == "charpy_area":
            flags.append("impact_method_inferred:charpy")
            return PROP_BY_KEY["impact_charpy"], flags
        if method_family == "iso_izod_area":
            flags.append("impact_method_inferred:iso_izod_area")
            return PROP_BY_KEY["impact_izod_area"], flags
        if method_family == "astm_izod_linear" or unit_family == "linear":
            flags.append("impact_method_inferred:astm_izod")
            return PROP_BY_KEY["impact_izod"], flags
        return prop, flags

    if prop.key == "impact_charpy" and unit_family == "linear":
        flags.append("impact_method_unit_mismatch:linear_unit_under_charpy_key")
    return prop, flags


def infer_linear_izod_method(text: str) -> str | None:
    m = re.search(r"\bASTM\s*D\s*(?:256|4812)\b", text, re.I)
    return compact_spaces(m.group(0)).upper() if m else None


def append_ft_lbf_impact_observations(
    observations: list[dict[str, Any]],
    seen: set[tuple[Any, ...]],
    windows: list[str],
    source: dict[str, Any] | None,
) -> None:
    prop = PROP_BY_KEY["impact_izod"]
    for ctx in windows:
        if not has_ft_lbf_per_in(ctx) or not re.search(r"\b(?:Izod|ASTM\s*D\s*(?:256|4812))\b", ctx, re.I):
            continue
        raw_match = re.search(rf"({NUM})\s*ft[-.]?(?:lb|lbf)/in", ctx, re.I)
        if not raw_match:
            continue
        raw_val = raw_match.group(1)
        value_min, value_max, value_nominal, quality = parse_numeric(raw_val, "ft-lb/in", prop.canonical_unit)
        quality = append_quality_flag(quality, "impact_method_inferred:astm_izod")
        if not is_plausible(prop.key, value_nominal):
            record_rejection(source, prop, raw_val, "outside_plausible_range", ctx)
            continue
        key = (
            prop.key,
            raw_val,
            "ft-lb/in",
            round(value_nominal or -999999, 5) if value_nominal is not None else None,
            infer_orientation(ctx),
            infer_condition(ctx),
        )
        if key in seen:
            continue
        seen.add(key)
        observations.append(
            {
                "property_key": prop.key,
                "property_label": prop.label,
                "category": prop.category,
                "raw_label": "Izod impact inferred from ft-lb/in unit",
                "raw_value": raw_val,
                "unit_raw": "ft-lb/in",
                "unit_canonical": prop.canonical_unit,
                "value_min": value_min,
                "value_max": value_max,
                "value_nominal": value_nominal,
                "test_method": infer_linear_izod_method(ctx) or infer_method(ctx),
                "orientation": infer_orientation(ctx),
                "condition": infer_condition(ctx),
                "source_context": ctx[:500],
                "quality_flag": quality or None,
            }
        )


def context_windows(text: str, row_texts: list[str]) -> list[str]:
    windows = list(row_texts)
    lines = [compact_spaces(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    for i, line in enumerate(lines):
        window = " | ".join(lines[i : i + 6])
        if window:
            windows.append(window)
    return windows


def extract_observations(text: str, rows: list[str], source: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    seen = set()
    windows = context_windows(text, rows)

    for prop in PROPERTY_DEFS:
        if not prop.patterns:
            continue
        pat = property_patterns(prop)
        for ctx in windows:
            if not pat.search(ctx):
                continue
            audit_rejected_candidates(ctx, prop, pat, source)
            lower_ctx = ctx.lower()
            if any(skip in lower_ctx for skip in ("not applicable", "n/a", "no break", "disclaimer")):
                if prop.key not in {"impact_charpy", "impact_strength"}:
                    continue
            if prop.key == "diameter" and "diameter tolerance" in lower_ctx:
                continue
            if prop.key == "impact_strength" and ("izod" in lower_ctx or "charpy" in lower_ctx):
                continue
            if prop.key == "hardness_shore_d" and "shore a" in lower_ctx:
                continue
            if prop.key == "hardness_shore_a" and "shore d" in lower_ctx:
                continue
            # Avoid interpreting print/specimen dimensions as filament diameter.
            if prop.key == "diameter" and any(x in lower_ctx for x in ("nozzle", "specimen", "spool", "fiberon website")):
                continue
            unit_raw = detect_unit(ctx, prop)
            resolved_prop = prop
            if prop.canonical_unit == "rating":
                raw_val = None
                rating_match = re.search(r"\b(HB|V-0|V-1|V-2|Good|Fair|Poor|Flammable|Not resistant|Resistant[^|,;]*)\b", ctx, re.I)
                if rating_match:
                    raw_val = rating_match.group(0)
                else:
                    continue
                value_min = value_max = value_nominal = None
                quality = "categorical"
            else:
                raw_val = choose_raw_value(ctx, prop, pat)
                if not raw_val:
                    continue
                resolved_prop, impact_flags = resolve_impact_property(prop, ctx, unit_raw or prop.canonical_unit)
                if any(flag.startswith("impact_method_unit_mismatch") for flag in impact_flags):
                    record_rejection(source, resolved_prop, raw_val, "impact_method_unit_mismatch", ctx)
                    continue
                value_min, value_max, value_nominal, quality = parse_numeric(
                    raw_val,
                    unit_raw or resolved_prop.canonical_unit,
                    resolved_prop.canonical_unit,
                )
                for flag in impact_flags:
                    quality = append_quality_flag(quality, flag)
                if not is_plausible(resolved_prop.key, value_nominal):
                    record_rejection(source, resolved_prop, raw_val, "outside_plausible_range", ctx)
                    continue
            key = (
                resolved_prop.key,
                raw_val,
                unit_raw,
                round(value_nominal or -999999, 5) if value_nominal is not None else None,
                infer_orientation(ctx),
                infer_condition(ctx),
            )
            if key in seen:
                continue
            seen.add(key)
            observation_ctx = local_observation_context(ctx, pat, raw_val)
            observations.append(
                {
                    "property_key": resolved_prop.key,
                    "property_label": resolved_prop.label,
                    "category": resolved_prop.category,
                    "raw_label": compact_spaces((pat.search(ctx).group(0) if pat.search(ctx) else prop.label)),
                    "raw_value": raw_val,
                    "unit_raw": unit_raw,
                    "unit_canonical": resolved_prop.canonical_unit,
                    "value_min": value_min,
                    "value_max": value_max,
                    "value_nominal": value_nominal,
                    "test_method": infer_method(observation_ctx),
                    "orientation": infer_orientation(ctx),
                    "condition": infer_condition(ctx),
                    "source_context": observation_ctx,
                    "quality_flag": quality or None,
                }
            )
    append_ft_lbf_impact_observations(observations, seen, windows, source)
    return observations


def parse_json_profiles() -> list[dict[str, Any]]:
    rows = []
    for path in DATASHEET_ROOT.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        supplier = supplier_from_path(path)
        product = compact_spaces(str(data.get("name") or strip_product_from_filename(path, supplier)))
        base, family, modifiers = classify_material(product)
        material_id = f"{supplier}|{product}|profile|{path.relative_to(ROOT).as_posix()}"
        obs = []
        mapping = {
            "filament_density": ("density", "g/cm3"),
            "temperature_vitrification": ("glass_transition", "degC"),
            "nozzle_temperature": ("nozzle_temperature", "degC"),
            "nozzle_temperature_initial_layer": ("nozzle_temperature", "degC"),
            "hot_plate_temp": ("bed_temperature", "degC"),
            "textured_plate_temp": ("bed_temperature", "degC"),
            "cool_plate_temp": ("bed_temperature", "degC"),
            "filament_max_volumetric_speed": ("max_volumetric_speed", "mm3/s"),
        }
        for field, (prop_key, unit) in mapping.items():
            if field not in data:
                continue
            val = data[field][0] if isinstance(data[field], list) and data[field] else data[field]
            prop = PROP_BY_KEY[prop_key]
            vmin, vmax, vnom, flag = parse_numeric(str(val), unit, prop.canonical_unit)
            obs.append(
                {
                    "property_key": prop_key,
                    "property_label": prop.label,
                    "category": prop.category,
                    "raw_label": field,
                    "raw_value": str(val),
                    "unit_raw": unit,
                    "unit_canonical": prop.canonical_unit,
                    "value_min": vmin,
                    "value_max": vmax,
                    "value_nominal": vnom,
                    "test_method": None,
                    "orientation": None,
                    "condition": "slicer profile",
                    "source_context": field,
                    "quality_flag": flag or "profile_value",
                }
            )
        if obs:
            rows.append(
                {
                    "material_id": material_id,
                    "supplier": supplier,
                    "product": product,
                    "base_material": base,
                    "material_family": family,
                    "modifiers": modifiers,
                    "source_type": "json_profile",
                    "source_file": path.relative_to(ROOT).as_posix(),
                    "pages": None,
                    "status": "parsed",
                    "quality_notes": "Slicer profile, not a formal material TDS.",
                    "observations": obs,
                }
            )
    return rows


def load_html_spec_entries() -> list[dict[str, Any]]:
    if not HTML_SPECS_PATH.exists():
        return []
    try:
        data = json.loads(HTML_SPECS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    entries = data.get("entries", data) if isinstance(data, dict) else data
    if isinstance(entries, dict):
        entries = list(entries.values())
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def parse_html_specs() -> list[dict[str, Any]]:
    materials: list[dict[str, Any]] = []
    for idx, entry in enumerate(load_html_spec_entries()):
        supplier = compact_spaces(str(entry.get("supplier") or "Unknown"))
        product = compact_spaces(str(entry.get("product") or entry.get("title") or "Unknown product"))
        source_file = compact_spaces(str(entry.get("source_file") or ""))
        source_url = compact_spaces(str(entry.get("source_url") or ""))
        raw_rows = entry.get("rows") or []
        rows = [compact_spaces(str(row)) for row in raw_rows if compact_spaces(str(row))]
        text = clean_text("\n".join(str(part) for part in (entry.get("text") or "", "\n".join(rows)) if part))
        observations = extract_observations(
            text,
            rows,
            {
                "supplier": supplier,
                "product": product,
                "source_type": "html_spec",
                "source_file": source_file or source_url,
            },
        )
        for obs in observations:
            obs["quality_flag"] = append_quality_flag(obs.get("quality_flag"), "official_html_specs")
        base, family, modifiers = classify_material(product)
        status = "parsed" if observations else "no_properties_found"
        notes = ["Official vendor product page/specification table; may be less formal than a TDS."]
        if not observations:
            notes.append("No target properties were found in normalized HTML rows.")
        source_id = source_url or source_file or f"html_spec_entry_{idx}"
        materials.append(
            {
                "material_id": f"{supplier}|{product}|html|{source_id}",
                "supplier": supplier,
                "product": product,
                "base_material": base,
                "material_family": family,
                "modifiers": modifiers,
                "source_type": "html_spec",
                "source_file": source_file or source_url,
                "pages": None,
                "status": status,
                "quality_notes": "; ".join(notes),
                "observations": observations,
            }
        )
    return materials


def parse_pdf_material(path: Path) -> dict[str, Any]:
    supplier = supplier_from_path(path)
    skip, skip_reason = should_skip_pdf(path)
    fallback_product = strip_product_from_filename(path, supplier)
    if skip:
        base, family, modifiers = classify_material(fallback_product)
        return {
            "material_id": f"{supplier}|{fallback_product}|pdf|{path.relative_to(ROOT).as_posix()}",
            "supplier": supplier,
            "product": fallback_product,
            "base_material": base,
            "material_family": family,
            "modifiers": modifiers,
            "source_type": "pdf",
            "source_file": path.relative_to(ROOT).as_posix(),
            "pages": None,
            "status": "skipped",
            "quality_notes": skip_reason,
            "observations": [],
        }
    needs_tables = supplier in {"Anycubic", "Bambu Lab", "MatterHackers", "Polymaker", "Prusa Polymers", "Ultimaker"} or "Bambu" in path.name
    text, rows, pages, error = read_pdf(path, extract_tables=needs_tables)
    native_text_len = len(compact_spaces(text))
    ocr_mode = None
    override = ocr_text_override(path) if not error else None
    if override and native_text_len < 80 and not rows:
        override_text, override_rows, ocr_mode = override
        text = clean_text("\n".join(part for part in (text, override_text) if part))
        rows.extend(override_rows)
    text_len = len(compact_spaces(text))
    product = extract_text_product(text, fallback_product) if text else fallback_product
    base, family, modifiers = classify_material(product)

    status = "parsed"
    notes = []
    observations: list[dict[str, Any]] = []
    if error:
        status = "error"
        notes.append(error)
    elif supplier == "Fiberlogy" and "polityka prywatno" in text.lower():
        status = "skipped"
        notes.append("privacy_policy_or_auxiliary")
    elif supplier == "Fiberlogy" and pages and pages > 5 and text_len < 80 and not rows:
        status = "skipped"
        notes.append("fiberlogy_catalog_or_auxiliary_image_pdf")
    elif text_len < 80 and not rows:
        status = "needs_ocr"
        notes.append("No usable text layer or tables.")
    else:
        observations = extract_observations(
            text,
            rows,
            {
                "supplier": supplier,
                "product": product,
                "source_type": "pdf",
                "source_file": path.relative_to(ROOT).as_posix(),
            },
        )
        if ocr_mode:
            notes.append(f"OCR/vision text sidecar: {ocr_mode}.")
            for obs in observations:
                obs["quality_flag"] = append_quality_flag(obs.get("quality_flag"), "ocr_or_vision_text")
        if not observations:
            status = "no_properties_found"
            notes.append("Opened successfully but no target properties were found.")
        if text_len < 300:
            notes.append("Low text volume; may require OCR.")

    return {
        "material_id": f"{supplier}|{product}|pdf|{path.relative_to(ROOT).as_posix()}",
        "supplier": supplier,
        "product": product,
        "base_material": base,
        "material_family": family,
        "modifiers": modifiers,
        "source_type": "pdf",
        "source_file": path.relative_to(ROOT).as_posix(),
        "pages": pages,
        "status": status,
        "quality_notes": "; ".join(notes),
        "observations": observations,
    }


def build_database(materials: list[dict[str, Any]]) -> None:
    ANALYSIS_DIR.mkdir(exist_ok=True)
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = DB_PATH.with_suffix(".sqlite.tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    con = sqlite3.connect(tmp_path)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode=DELETE")
    cur.executescript(
        """
        CREATE TABLE materials (
            material_id TEXT PRIMARY KEY,
            supplier TEXT,
            product TEXT,
            base_material TEXT,
            material_family TEXT,
            modifiers_json TEXT,
            source_type TEXT,
            source_file TEXT,
            pages INTEGER,
            status TEXT,
            quality_notes TEXT
        );
        CREATE TABLE property_definitions (
            property_key TEXT PRIMARY KEY,
            label TEXT,
            category TEXT,
            canonical_unit TEXT,
            radar INTEGER,
            higher_is_better INTEGER
        );
        CREATE TABLE observations (
            observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id TEXT,
            property_key TEXT,
            property_label TEXT,
            category TEXT,
            raw_label TEXT,
            raw_value TEXT,
            unit_raw TEXT,
            unit_canonical TEXT,
            value_min REAL,
            value_max REAL,
            value_nominal REAL,
            test_method TEXT,
            orientation TEXT,
            condition TEXT,
            source_context TEXT,
            quality_flag TEXT,
            FOREIGN KEY(material_id) REFERENCES materials(material_id)
        );
        CREATE INDEX idx_observations_property ON observations(property_key);
        CREATE INDEX idx_materials_base ON materials(base_material);
        """
    )
    cur.executemany(
        "INSERT INTO property_definitions VALUES (?,?,?,?,?,?)",
        [(p.key, p.label, p.category, p.canonical_unit, int(p.radar), int(p.higher_is_better)) for p in PROPERTY_DEFS],
    )
    for mat in materials:
        cur.execute(
            "INSERT INTO materials VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                mat["material_id"],
                mat["supplier"],
                mat["product"],
                mat["base_material"],
                mat["material_family"],
                json.dumps(mat["modifiers"], ensure_ascii=False),
                mat["source_type"],
                mat["source_file"],
                mat["pages"],
                mat["status"],
                mat["quality_notes"],
            ),
        )
        for obs in mat["observations"]:
            cur.execute(
                """
                INSERT INTO observations (
                    material_id, property_key, property_label, category, raw_label, raw_value,
                    unit_raw, unit_canonical, value_min, value_max, value_nominal,
                    test_method, orientation, condition, source_context, quality_flag
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    mat["material_id"],
                    obs["property_key"],
                    obs["property_label"],
                    obs["category"],
                    obs["raw_label"],
                    obs["raw_value"],
                    obs["unit_raw"],
                    obs["unit_canonical"],
                    obs["value_min"],
                    obs["value_max"],
                    obs["value_nominal"],
                    obs["test_method"],
                    obs["orientation"],
                    obs["condition"],
                    obs["source_context"],
                    obs["quality_flag"],
                ),
            )
    con.commit()
    integrity = cur.execute("PRAGMA integrity_check").fetchone()
    if not integrity or integrity[0] != "ok":
        con.close()
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")
    con.close()
    verify_con = sqlite3.connect(tmp_path)
    try:
        integrity = verify_con.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError(f"SQLite reopen integrity check failed: {integrity}")
    finally:
        verify_con.close()
    if DB_PATH.exists():
        DB_PATH.unlink()
    tmp_path.replace(DB_PATH)


def summarize(materials: list[dict[str, Any]]) -> dict[str, Any]:
    parsed = [m for m in materials if m["observations"]]
    all_obs = [obs | {"material_id": m["material_id"]} for m in materials for obs in m["observations"]]
    numeric_obs = [o for o in all_obs if isinstance(o.get("value_nominal"), (int, float))]
    coverage = []
    for prop in PROPERTY_DEFS:
        values = [o["value_nominal"] for o in numeric_obs if o["property_key"] == prop.key and o["value_nominal"] is not None]
        material_count = len({o["material_id"] for o in all_obs if o["property_key"] == prop.key})
        coverage.append(
            {
                "property_key": prop.key,
                "label": prop.label,
                "category": prop.category,
                "unit": prop.canonical_unit,
                "materials": material_count,
                "observations": len([o for o in all_obs if o["property_key"] == prop.key]),
                "numeric_values": len(values),
                "min": min(values) if values else None,
                "max": max(values) if values else None,
                "avg": mean(values) if values else None,
                "median": median(values) if values else None,
            }
        )
    groups: dict[str, Any] = {}
    for group_field in ("base_material", "material_family"):
        group_rows: dict[str, list[dict[str, Any]]] = {}
        for mat in parsed:
            key = mat[group_field] or "Unknown"
            group_rows.setdefault(key, []).append(mat)
        groups[group_field] = {key: len(vals) for key, vals in sorted(group_rows.items())}
    return {
        "material_count": len(materials),
        "parsed_material_count": len(parsed),
        "observation_count": len(all_obs),
        "numeric_observation_count": len(numeric_obs),
        "coverage": coverage,
        "groups": groups,
        "statuses": {status: len([m for m in materials if m["status"] == status]) for status in sorted({m["status"] for m in materials})},
    }


def write_exports(materials: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "material_id",
                "supplier",
                "product",
                "base_material",
                "material_family",
                "source_file",
                "property_key",
                "property_label",
                "raw_value",
                "unit_raw",
                "value_min",
                "value_max",
                "value_nominal",
                "unit_canonical",
                "test_method",
                "orientation",
                "condition",
                "quality_flag",
            ]
        )
        for mat in materials:
            for obs in mat["observations"]:
                writer.writerow(
                    [
                        mat["material_id"],
                        mat["supplier"],
                        mat["product"],
                        mat["base_material"],
                        mat["material_family"],
                        mat["source_file"],
                        obs["property_key"],
                        obs["property_label"],
                        obs["raw_value"],
                        obs["unit_raw"],
                        obs["value_min"],
                        obs["value_max"],
                        obs["value_nominal"],
                        obs["unit_canonical"],
                        obs["test_method"],
                        obs["orientation"],
                        obs["condition"],
                        obs["quality_flag"],
                    ]
                )
    export = {
        "generated_at": date.today().isoformat(),
        "properties": [p.__dict__ for p in PROPERTY_DEFS],
        "materials": materials,
        "summary": summary,
    }
    JSON_PATH.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Property Tag Study",
        "",
        "This full-corpus pass uses tags for every property family the parser can currently recognize. Tags are intentionally more granular than UI labels so that PETG-CF, Matte PLA, PLA Basic, and other variants can remain distinct while still rolling up to a base material when requested.",
        "",
        f"- Source PDFs discovered: {len(list(DATASHEET_ROOT.rglob('*.pdf')))}",
        f"- Material/source records in database: {summary['material_count']}",
        f"- Records with extracted observations: {summary['parsed_material_count']}",
        f"- Extracted observations: {summary['observation_count']}",
        "",
        "## Tags",
        "",
        "| Tag | Label | Category | Canonical unit | Records | Numeric values | DB min | DB max | Radar axis |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    cov_by_key = {c["property_key"]: c for c in summary["coverage"]}
    for prop in PROPERTY_DEFS:
        cov = cov_by_key[prop.key]
        lines.append(
            f"| `{prop.key}` | {prop.label} | {prop.category} | {prop.canonical_unit} | "
            f"{cov['materials']} | {cov['numeric_values']} | {fmt(cov['min'])} | {fmt(cov['max'])} | {'Y' if prop.radar else ''} |"
        )
    lines.extend(
        [
            "",
            "## Important Modeling Tags",
            "",
            "- `base_material`: broad chemistry such as PLA, PETG, ABS, ASA, PC, PA, TPU.",
            "- `material_family`: closer material signature such as PLA-CF, PETG-CF, PA6-CF, PC-ABS. This is the default for similar-material spread so Matte PLA is not treated as PLA Basic.",
            "- `modifiers`: product descriptors such as Matte, Basic, Carbon fiber, Glass fiber, ESD, Recycled, High speed, Support, Flame retardant.",
            "- `orientation`: X-Y, XY, YZ, Z, flat, side, up, horizontal, vertical.",
            "- `condition`: dry, wet, annealed, dried, notched, unnotched, yield, break, HDT load condition.",
            "- `test_method`: ASTM, ISO, GB/T, IEC, DIN, DSC, TGA, UL when present.",
            "- `source_type`: PDF datasheet, official HTML product/spec page, or slicer JSON profile.",
            "- `quality_flag`: parser/conversion notes, source anomalies, categorical values, profile values, OCR needs.",
            "",
            "## Unit Policy",
            "",
            "- Stress and modulus are stored in MPa.",
            "- Temperatures are stored in degC.",
            "- Density is stored in g/cm3.",
            "- MFR/MFI is stored in g/10min.",
            "- Charpy-style impact values are stored in kJ/m2.",
            "- ASTM-style linear Izod impact values are stored in J/m; ft-lb/in values are converted to J/m and flagged.",
            "- ISO/area-normalized Izod impact values are stored separately in kJ/m2 because they are not dimensionally equivalent to J/m.",
            "- Raw value, raw unit, canonical unit, normalized min/max/nominal, and source context are retained for auditability.",
        ]
    )
    TAG_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audit_report() -> None:
    ANALYSIS_DIR.mkdir(exist_ok=True)
    payload = {
        "generated_at": date.today().isoformat(),
        "rejection_count": len(AUDIT_REJECTIONS),
        "rejections": AUDIT_REJECTIONS,
    }
    AUDIT_JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Material Database Audit",
        "",
        f"Generated: {payload['generated_at']}",
        f"Rejected candidate observations: {payload['rejection_count']}",
        "",
        "| Supplier | Product | Property | Raw value | Reason |",
        "|---|---|---|---:|---|",
    ]
    for row in AUDIT_REJECTIONS[:500]:
        lines.append(
            "| {supplier} | {product} | `{property_key}` | {raw_value} | {reason} |".format(
                supplier=str(row.get("supplier") or "").replace("|", "/"),
                product=str(row.get("product") or "").replace("|", "/"),
                property_key=row.get("property_key") or "",
                raw_value=str(row.get("raw_value") or "").replace("|", "/"),
                reason=row.get("reason") or "",
            )
        )
    if len(AUDIT_REJECTIONS) > 500:
        lines.append("")
        lines.append(f"Only the first 500 rejected candidates are shown here. See `{AUDIT_JSON_PATH.name}` for the full audit.")
    AUDIT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isfinite(value):
            return f"{value:.3g}"
    return str(value)


def main() -> None:
    AUDIT_REJECTIONS.clear()
    AUDIT_REJECTION_KEYS.clear()
    pdf_materials = [parse_pdf_material(path) for path in sorted(DATASHEET_ROOT.rglob("*.pdf"))]
    profile_materials = parse_json_profiles()
    html_materials = parse_html_specs()
    materials = pdf_materials + profile_materials + html_materials
    summary = summarize(materials)
    build_database(materials)
    write_exports(materials, summary)
    write_audit_report()
    print(json.dumps({
        "db": str(DB_PATH),
        "json": str(JSON_PATH),
        "csv": str(CSV_PATH),
        "report": str(TAG_REPORT_PATH),
        "audit_json": str(AUDIT_JSON_PATH),
        "audit_md": str(AUDIT_MD_PATH),
        "summary": summary,
    }, indent=2))


if __name__ == "__main__":
    main()
