from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MATERIALS_JSON = ROOT / "web" / "data" / "materials.json"
ANALYSIS_DIR = ROOT / "analysis"
REPORT_MD = ANALYSIS_DIR / "material_property_issue_audit_20260607.md"
REPORT_JSON = ANALYSIS_DIR / "material_property_issue_audit_20260607.json"
REPORT_CSV = ANALYSIS_DIR / "material_property_issue_audit_20260607.csv"


METHOD_CAPTURE_CODES = {
    "527": ("ISO 527", "tensile test standard code captured as the value"),
    "178": ("ISO 178", "flexural test standard code captured as the value"),
    "179": ("ISO 179", "impact test standard code captured as the value"),
    "306": ("ISO 306", "Vicat test standard code captured as the value"),
    "306.10": ("ISO 306 / 10N", "Vicat test standard and load captured as the value"),
    "1183": ("ISO 1183", "density test standard code captured as the value"),
    "257": ("ASTM D257", "electrical resistance test standard code captured as the value"),
    "638": ("ASTM D638", "tensile test standard code captured as the value"),
    "790": ("ASTM D790", "flexural test standard code captured as the value"),
}

HIGH_RIGID_ELONGATION_LIMIT = 100.0
LOW_RIGID_MODULUS_LIMIT = 100.0

FLEXIBLE_WORDS = re.compile(r"\b(TPU|TPE|PEBA|flex|varioshore|shore\s*[aA])\b", re.I)

PROPERTY_HINTS: list[tuple[str, re.Pattern[str]]] = [
    ("diameter_tolerance", re.compile(r"diameter\s+tolerance|tolerance", re.I)),
    ("diameter", re.compile(r"\bdiameter\b", re.I)),
    ("net_weight", re.compile(r"net\s+(?:filament\s+)?weight|spool\s+weight", re.I)),
    ("filament_length", re.compile(r"filament\s+length", re.I)),
    ("nozzle_temperature", re.compile(r"nozzle|extrusion|extruder|print\s+temperature", re.I)),
    ("bed_temperature", re.compile(r"\bbed\b|build\s+(?:plate|platform)", re.I)),
    ("chamber_temperature", re.compile(r"chamber", re.I)),
    ("drying_temperature", re.compile(r"dry(?:ing)?\s+(?:environment|temperature|temp)", re.I)),
    ("annealing_temperature", re.compile(r"anneal", re.I)),
    ("print_speed", re.compile(r"print(?:ing)?\s+speed", re.I)),
    ("density", re.compile(r"(?<!infill\s)\bdensity\b|specific\s+gravity", re.I)),
    ("melt_flow_index", re.compile(r"melt\s+(?:flow|index)|\bMFI\b|\bMFR\b", re.I)),
    ("melt_volume_rate", re.compile(r"\bMVR\b|melt\s+volume", re.I)),
    ("water_absorption", re.compile(r"water|moisture\s+absorption", re.I)),
    ("shrinkage", re.compile(r"shrinkage", re.I)),
    ("tensile_strength", re.compile(r"tensile\s+(?:yield\s+)?(?:strength|stress)", re.I)),
    ("tensile_modulus", re.compile(r"(?:young'?s|tensile)\s+modulus", re.I)),
    ("elongation", re.compile(r"elongation|strain", re.I)),
    ("flexural_strength", re.compile(r"(?:flexural|bending)\s+strength", re.I)),
    ("flexural_modulus", re.compile(r"(?:flexural|bending)\s+modulus", re.I)),
    ("impact", re.compile(r"(?:charpy|izod|impact)\s+(?:strength|impact)", re.I)),
    ("hardness", re.compile(r"hardness|shore", re.I)),
    ("hdt", re.compile(r"heat\s+(?:deflection|distortion)|\bHDT\b|deflection\s+temperature", re.I)),
    ("vicat", re.compile(r"vicat|vicar|VST", re.I)),
    ("glass_transition", re.compile(r"glass\s+transition|\bTg\b", re.I)),
    ("melting_temperature", re.compile(r"melting|melt\s+temperature", re.I)),
    ("crystallization_temperature", re.compile(r"crystallization", re.I)),
    ("surface_resistance", re.compile(r"surface\s+resist", re.I)),
    ("insulation_resistance", re.compile(r"insulation\s+resist", re.I)),
    ("flame_retardancy", re.compile(r"flame\s+retard|flammability", re.I)),
    ("chemical_resistance", re.compile(r"chemical\s+resistance|effect\s+of", re.I)),
]

PROPERTY_EQUIVALENCE = {
    "impact_charpy": {"impact"},
    "impact_izod": {"impact"},
    "impact_strength": {"impact"},
    "hardness_shore_a": {"hardness"},
    "hardness_shore_d": {"hardness"},
}


@dataclass(frozen=True)
class Issue:
    confidence: str
    issue_type: str
    supplier: str
    product: str
    property_key: str
    raw_value: str
    value_nominal: Any
    unit_raw: str
    unit_canonical: str
    source_file: str
    evidence: str
    suggested_action: str
    test_method: str = ""
    orientation: str = ""
    condition: str = ""
    quality_flag: str = ""
    source_context: str = ""
    material_family: str = ""
    base_material: str = ""

    @property
    def issue_id(self) -> str:
        digest = hashlib.sha1(
            "\n".join(
                [
                    self.issue_type,
                    self.supplier,
                    self.product,
                    self.property_key,
                    self.raw_value,
                    self.source_file,
                    self.source_context[:160],
                ]
            ).encode("utf-8")
        ).hexdigest()[:12]
        return f"{self.confidence[:1].upper()}-{digest}"

    def as_dict(self) -> dict[str, Any]:
        data = {
            "issue_id": self.issue_id,
            "confidence": self.confidence,
            "issue_type": self.issue_type,
            "supplier": self.supplier,
            "product": self.product,
            "base_material": self.base_material,
            "material_family": self.material_family,
            "property_key": self.property_key,
            "raw_value": self.raw_value,
            "value_nominal": self.value_nominal,
            "unit_raw": self.unit_raw,
            "unit_canonical": self.unit_canonical,
            "test_method": self.test_method,
            "orientation": self.orientation,
            "condition": self.condition,
            "quality_flag": self.quality_flag,
            "source_file": self.source_file,
            "evidence": self.evidence,
            "suggested_action": self.suggested_action,
            "source_context": self.source_context,
        }
        return data


def load_database() -> dict[str, Any]:
    return json.loads(MATERIALS_JSON.read_text(encoding="utf-8"))


def compact(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def norm_raw(raw: Any) -> str:
    value = compact(raw).replace("±", "+/-").replace(" ", "")
    value = value.lstrip("<>")
    return value


def cells(ctx: str) -> list[str]:
    return [compact(part) for part in str(ctx or "").split("|") if compact(part)]


def raw_in_cell(raw_value: str, cell: str) -> bool:
    raw = compact(raw_value).replace("±", "+/-")
    if not raw:
        return False
    normalized_cell = compact(cell).replace("±", "+/-")
    compact_raw = raw.replace(" ", "")
    compact_cell = normalized_cell.replace(" ", "")
    return raw in normalized_cell or compact_raw in compact_cell


def nearest_label_for_raw(ctx: str, raw_value: str) -> tuple[str | None, int | None, int | None, list[str]]:
    parts = cells(ctx)
    raw_index = None
    for idx, part in enumerate(parts):
        if raw_in_cell(raw_value, part):
            raw_index = idx
            break
    if raw_index is None:
        return None, None, None, parts
    for idx in range(raw_index, -1, -1):
        for key, pattern in PROPERTY_HINTS:
            if pattern.search(parts[idx]):
                return key, idx, raw_index, parts
    return None, None, raw_index, parts


def prop_matches_hint(prop_key: str, hint: str | None) -> bool:
    if not hint:
        return True
    if prop_key == hint:
        return True
    if hint in PROPERTY_EQUIVALENCE.get(prop_key, set()):
        return True
    if prop_key in {"impact_charpy", "impact_izod", "impact_strength"} and hint == "impact":
        return True
    if prop_key in {"hardness_shore_a", "hardness_shore_d"} and hint == "hardness":
        return True
    return False


def source_orientation_from_cell(label: str | None) -> str | None:
    if not label:
        return None
    text = label.upper()
    if re.search(r"\(Z\)|\bZ\b", text):
        return "Z"
    if re.search(r"\(Y[- ]?Z\)|\bYZ\b", text):
        return "YZ"
    if re.search(r"\(X[- ]?Y\)|\bX[- ]?Y\b", text):
        return "X-Y"
    return None


def source_method_near_raw(parts: list[str], raw_index: int | None) -> str | None:
    if raw_index is None:
        return None
    text = " | ".join(parts[max(0, raw_index - 4) : raw_index + 1])
    matches = re.findall(r"\b(?:ISO|ASTM|GB/T|IEC|DIN|UL)\s*[-/]?\s*[A-Z]?\s*\d+(?:[-/]\d+)?", text, re.I)
    if not matches:
        return None
    return compact(matches[-1]).upper()


def material_text(material: dict[str, Any]) -> str:
    return " ".join(
        compact(material.get(key))
        for key in ("supplier", "product", "base_material", "material_family", "quality_notes")
    )


def is_flexible(material: dict[str, Any]) -> bool:
    return bool(FLEXIBLE_WORDS.search(material_text(material)))


def issue(
    confidence: str,
    issue_type: str,
    material: dict[str, Any],
    observation: dict[str, Any],
    evidence: str,
    suggested_action: str,
) -> Issue:
    return Issue(
        confidence=confidence,
        issue_type=issue_type,
        supplier=compact(material.get("supplier")),
        product=compact(material.get("product")),
        base_material=compact(material.get("base_material")),
        material_family=compact(material.get("material_family")),
        property_key=compact(observation.get("property_key")),
        raw_value=compact(observation.get("raw_value")),
        value_nominal=observation.get("value_nominal"),
        unit_raw=compact(observation.get("unit_raw")),
        unit_canonical=compact(observation.get("unit_canonical")),
        test_method=compact(observation.get("test_method")),
        orientation=compact(observation.get("orientation")),
        condition=compact(observation.get("condition")),
        quality_flag=compact(observation.get("quality_flag")),
        source_file=compact(material.get("source_file")),
        evidence=compact(evidence),
        suggested_action=compact(suggested_action),
        source_context=compact(observation.get("source_context")),
    )


def detect_issues(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []

    for material in data.get("materials") or []:
        for observation in material.get("observations") or []:
            prop = compact(observation.get("property_key"))
            raw = compact(observation.get("raw_value"))
            normalized_raw = norm_raw(raw)
            ctx = compact(observation.get("source_context"))
            lower_ctx = ctx.lower()
            value = observation.get("value_nominal")
            method = compact(observation.get("test_method"))
            unit_raw = compact(observation.get("unit_raw"))
            label_hint, label_index, raw_index, part_list = nearest_label_for_raw(ctx, raw)
            label_cell = part_list[label_index] if label_index is not None else ""

            if normalized_raw in METHOD_CAPTURE_CODES:
                method_name, explanation = METHOD_CAPTURE_CODES[normalized_raw]
                method_token = method_name.replace(" ", "")
                if method_token.lower() in lower_ctx.replace(" ", "") or method_token.lower() in method.lower().replace(" ", ""):
                    issues.append(
                        issue(
                            "high",
                            "test_method_code_captured_as_property_value",
                            material,
                            observation,
                            f"{explanation}; source context shows `{method_name}` near the parsed value.",
                            "Drop this observation and parse the numeric value after the unit/value column, not the standard number.",
                        )
                    )

            if prop in {"surface_resistance", "insulation_resistance"}:
                if re.search(r"(?:[<>]=?\s*)?10\d{2}(?:\s*-\s*10\d{2})?", raw) or re.search(r"[x×]\s*10\d+", ctx, re.I):
                    issues.append(
                        issue(
                            "high",
                            "electrical_power_notation_flattened",
                            material,
                            observation,
                            "Electrical resistance uses power-of-ten notation in the datasheet, but the normalized value is stored as an ordinary small number.",
                            "Parse as scientific notation, e.g. `>10^13` as `>1e13`, and preserve the inequality/range.",
                        )
                    )
                elif normalized_raw in {"257", "1183"}:
                    issues.append(
                        issue(
                            "high",
                            "electrical_test_or_density_standard_captured",
                            material,
                            observation,
                            f"`{raw}` is a standards-code fragment in the source context, not a resistance value.",
                            "Reject standards-code fragments for electrical properties.",
                        )
                    )
                elif isinstance(value, (int, float)) and value <= 2 and ("mpa" in lower_ctx or "resistivity" in lower_ctx):
                    issues.append(
                        issue(
                            "high",
                            "electrical_value_captured_from_neighboring_field",
                            material,
                            observation,
                            "The source context points at a load condition, chart tick, or mantissa rather than a complete resistance value.",
                            "Reparse electrical rows with exponent-aware extraction and ignore nearby HDT/load/chart values.",
                        )
                    )
                elif "printing filament" in lower_ctx or "160-300" in raw:
                    issues.append(
                        issue(
                            "high",
                            "electrical_property_captured_from_commercial_text",
                            material,
                            observation,
                            "The value comes from a temperature/marketing bullet, not an electrical resistance measurement.",
                            "Drop this observation unless a true resistance row is present.",
                        )
                    )

            if prop == "density" and "infill density" in lower_ctx:
                issues.append(
                    issue(
                        "high",
                        "infill_density_captured_as_material_density",
                        material,
                        observation,
                        "The datasheet row is specimen print infill density, not resin/material density.",
                        "Drop this density observation and keep only density rows with material-density labels and units.",
                    )
                )

            if prop in {"impact_charpy", "impact_izod", "impact_strength"}:
                if "version: 3.0" in lower_ctx and re.fullmatch(r"3(?:\.0+)?", normalized_raw):
                    issues.append(
                        issue(
                            "high",
                            "document_version_captured_as_impact_value",
                            material,
                            observation,
                            "The source impact value is unavailable or `/`; the parsed number is the document version.",
                            "Drop version-number captures and treat `/`, `N/A`, or blank orientation rows as missing.",
                        )
                    )
                if ("not applicable" in lower_ctx or "no break" in lower_ctx) and re.fullmatch(r"[1-5](?:\.0+)?", normalized_raw):
                    issues.append(
                        issue(
                            "high",
                            "not_applicable_impact_row_published_as_number",
                            material,
                            observation,
                            "The datasheet says the impact result is not applicable/no break; the published number is a footnote or neighboring token.",
                            "Represent this as categorical/no-break metadata or omit from numeric charts.",
                        )
                    )
                if re.search(r"\[[^\]]*kJ/m\s*2[^\]]*\]\s*\(\d+\)", ctx, re.I) and re.fullmatch(r"[1-5](?:\.0+)?", normalized_raw):
                    issues.append(
                        issue(
                            "high",
                            "impact_footnote_marker_captured_as_value",
                            material,
                            observation,
                            "The number matches a footnote marker attached to the impact-unit label.",
                            "Reject footnote markers in unit labels before numeric extraction.",
                        )
                    )

            if prop in {"tensile_strength", "tensile_modulus", "flexural_strength", "flexural_modulus", "elongation"}:
                if label_hint and not prop_matches_hint(prop, label_hint):
                    # This is strongest when the source unit around the raw cell belongs to the other property family.
                    nearby = " | ".join(part_list[max(0, (raw_index or 0) - 3) : (raw_index or 0) + 2])
                    if (
                        ("%" in nearby and prop != "elongation")
                        or ("kj/m" in nearby.lower() and prop not in {"impact_charpy", "impact_izod", "impact_strength"})
                        or ("g/cm" in nearby.lower() and prop != "density")
                        or ("mpa" in nearby.lower() and prop == "elongation")
                    ):
                        issues.append(
                            issue(
                                "high",
                                "neighboring_property_value_captured",
                                material,
                                observation,
                                f"The nearest source label to `{raw}` is `{label_cell}`, not `{prop}`.",
                                "Anchor extraction to the nearest property label/value row and reject values following a different property label.",
                            )
                        )

                nearby = " | ".join(part_list[max(0, (raw_index or 0) - 3) : (raw_index or 0) + 2])
                if prop in {"tensile_strength", "tensile_modulus", "flexural_strength", "flexural_modulus"} and isinstance(value, (int, float)):
                    if value <= 5 and ("mm/min" in nearby.lower() or "mm / min" in nearby.lower()):
                        issues.append(
                            issue(
                                "high",
                                "test_speed_captured_as_mechanical_property",
                                material,
                                observation,
                                "The parsed mechanical value is a test speed in mm/min, not the strength/modulus result.",
                                "Ignore method speed/load cells when extracting mechanical property values.",
                            )
                        )

            if prop == "print_speed" and isinstance(value, (int, float)) and value < 5:
                if "extrusion multiplier" in lower_ctx or "diameter" in lower_ctx or "1.75" in normalized_raw:
                    issues.append(
                        issue(
                            "high",
                            "print_speed_captured_from_multiplier_or_diameter",
                            material,
                            observation,
                            "The parsed print speed is actually an extrusion multiplier, filament diameter, or nearby non-speed field.",
                            "Only accept values tied to the print/infill-speed row and an explicit `mm/s` speed value.",
                        )
                    )

            if prop == "nozzle_temperature" and isinstance(value, (int, float)) and value < 150:
                if "print speed" in lower_ctx or "40-250" in raw:
                    issues.append(
                        issue(
                            "high",
                            "nozzle_temperature_captured_from_print_speed",
                            material,
                            observation,
                            "The low nozzle-temperature range comes from a print-speed row, not the nozzle-temperature row.",
                            "Anchor nozzle temperature extraction to the nozzle/extruder label and reject speed ranges.",
                        )
                    )

            if prop == "chamber_temperature" and isinstance(value, (int, float)) and value < 20:
                issues.append(
                    issue(
                        "high",
                        "chamber_temperature_captured_from_note_number",
                        material,
                        observation,
                        "The parsed chamber temperature is a numbered note/list item, not a temperature value.",
                        "Reject note/list numbers and require a temperature unit near chamber values.",
                    )
                )

            if prop == "annealing_temperature" and isinstance(value, (int, float)) and value > 200:
                if label_hint and label_hint != "annealing_temperature":
                    issues.append(
                        issue(
                            "high",
                            "annealing_temperature_captured_from_neighboring_print_setting",
                            material,
                            observation,
                            f"The nearest source label is `{label_cell}`, so the value is not an annealing temperature.",
                            "Parse annealing settings only from rows labeled annealing/anneal and preserve time as separate metadata.",
                        )
                    )

            if prop == "melt_flow_index" and isinstance(value, (int, float)) and value > 150:
                if "°c" in lower_ctx or "℃" in lower_ctx or "kg" in lower_ctx:
                    issues.append(
                        issue(
                            "high",
                            "mfi_test_temperature_captured_as_flow_value",
                            material,
                            observation,
                            "The value is the MFI test temperature/load, not the melt-flow result.",
                            "Parse the flow result after the g/10min unit and keep test temperature/load as conditions.",
                        )
                    )

            if prop == "filament_length" and isinstance(value, (int, float)) and value < 10:
                if "1.75mm" in lower_ctx and re.search(r"\b3[0-9]{2}\s*-\s*3[0-9]{2}\s*m", lower_ctx):
                    issues.append(
                        issue(
                            "high",
                            "filament_diameter_captured_as_length",
                            material,
                            observation,
                            "The parsed filament length is the filament diameter in parentheses; the source row lists a 330-340 m length range.",
                            "Ignore diameter tokens in length rows and parse the meter range.",
                        )
                    )

            if prop in {"tensile_modulus", "flexural_modulus"} and isinstance(value, (int, float)) and value < 100:
                if re.fullmatch(r"\d{1,2}\.\d{3}", compact(raw)) and raw.replace(".", ",") in ctx:
                    issues.append(
                        issue(
                            "high",
                            "thousands_separator_parsed_as_decimal",
                            material,
                            observation,
                            "A thousands comma in the datasheet was normalized to a decimal point, shrinking the modulus by 1000x.",
                            "Treat comma-grouped three-digit suffixes as thousands separators for MPa modulus values.",
                        )
                    )

            if prop == "vicat" and normalized_raw in {"306", "306.10"}:
                issues.append(
                    issue(
                        "high",
                        "vicat_method_and_load_captured_as_temperature",
                        material,
                        observation,
                        "The datasheet context shows ISO 306 / 10N followed by the real Vicat temperature.",
                        "Drop the 306/306.10 observation and parse the temperature after the unit column.",
                    )
                )

            if prop in {"impact_izod", "impact_strength"} and unit_raw.lower() in {"kj/m2", "kj/m²"}:
                issues.append(
                    issue(
                        "medium",
                        "impact_method_unit_semantics_ambiguous",
                        material,
                        observation,
                        "The database stores an area-normalized kJ/m2 impact value under an Izod/generic key whose canonical unit is not area-normalized.",
                        "Split impact properties by method and unit, or keep this out of cross-method charts until normalized semantics are explicit.",
                    )
                )

            if prop != "hdt" and ("0.45 mpa load" in lower_ctx or "1.8 mpa load" in lower_ctx) and observation.get("condition"):
                if any(load in compact(observation.get("condition")).lower() for load in ("0.45 mpa load", "1.8 mpa load")):
                    issues.append(
                        issue(
                            "medium",
                            "hdt_load_condition_bleeds_into_other_property",
                            material,
                            observation,
                            "An HDT load condition was attached to a non-HDT observation because the parser window spans neighboring rows.",
                            "Infer conditions from the property's own row only.",
                        )
                    )

            source_orient = source_orientation_from_cell(label_cell)
            parsed_orient = compact(observation.get("orientation"))
            if source_orient and parsed_orient and source_orient != parsed_orient:
                issues.append(
                    issue(
                        "medium",
                        "orientation_metadata_mismatch",
                        material,
                        observation,
                        f"The nearest source label indicates `{source_orient}`, but the observation stores `{parsed_orient}`.",
                        "Infer orientation from the nearest property label rather than the whole context window.",
                    )
                )

            if prop == "elongation" and isinstance(value, (int, float)) and value > HIGH_RIGID_ELONGATION_LIMIT and not is_flexible(material):
                if normalized_raw not in METHOD_CAPTURE_CODES:
                    issues.append(
                        issue(
                            "uncertain",
                            "high_elongation_outlier_for_rigid_material",
                            material,
                            observation,
                            "The value is high for a nominally rigid filament family; some nylons/co-polyesters can be ductile, so this needs source review.",
                            "Verify whether this is filament/raw-resin data, printed-specimen data, a yield/break mix-up, or a parser capture error.",
                        )
                    )

            if prop in {"tensile_modulus", "flexural_modulus"} and isinstance(value, (int, float)) and 0 < value < LOW_RIGID_MODULUS_LIMIT and not is_flexible(material):
                issues.append(
                    issue(
                        "uncertain",
                        "very_low_modulus_outlier_for_rigid_material",
                        material,
                        observation,
                        "The modulus is far below normal rigid-thermoplastic stiffness unless this value came from a different property.",
                        "Verify against the source row and reject if the value belongs to elongation, impact, or another property.",
                    )
                )

    return dedupe_issues(issues)


def dedupe_issues(issues: list[Issue]) -> list[Issue]:
    seen: set[str] = set()
    first_pass: list[Issue] = []
    for item in issues:
        if item.issue_id in seen:
            continue
        seen.add(item.issue_id)
        first_pass.append(item)

    def obs_key(item: Issue) -> tuple[str, str, str, str, str]:
        return (item.source_file, item.product, item.property_key, item.raw_value, item.source_context[:240])

    types_by_obs: dict[tuple[str, str, str, str, str], set[str]] = defaultdict(set)
    high_obs: set[tuple[str, str, str, str, str]] = set()
    for item in first_pass:
        key = obs_key(item)
        types_by_obs[key].add(item.issue_type)
        if item.confidence == "high":
            high_obs.add(key)

    out: list[Issue] = []
    for item in first_pass:
        key = obs_key(item)
        if item.issue_type == "electrical_test_or_density_standard_captured" and "test_method_code_captured_as_property_value" in types_by_obs[key]:
            continue
        if item.issue_type == "test_method_code_captured_as_property_value" and "vicat_method_and_load_captured_as_temperature" in types_by_obs[key]:
            continue
        if item.confidence != "high" and key in high_obs:
            continue
        out.append(item)

    order = {"high": 0, "medium": 1, "uncertain": 2}
    out.sort(key=lambda x: (order.get(x.confidence, 9), x.issue_type, x.supplier, x.product, x.property_key, x.raw_value))
    return out


def write_csv(issues: list[Issue]) -> None:
    rows = [item.as_dict() for item in issues]
    if not rows:
        return
    with REPORT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def short(text: str, limit: int = 220) -> str:
    text = compact(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def write_markdown(issues: list[Issue], data: dict[str, Any]) -> None:
    by_conf = Counter(item.confidence for item in issues)
    by_type = Counter((item.confidence, item.issue_type) for item in issues)
    affected_materials = len({(item.supplier, item.product, item.source_file) for item in issues})
    affected_observations = len({(item.source_file, item.product, item.property_key, item.raw_value, item.source_context) for item in issues})

    lines: list[str] = []
    lines.append("# Material Property Issue Audit")
    lines.append("")
    lines.append("Generated: 2026-06-07")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(
        f"Crawled `web/data/materials.json` ({len(data.get('materials') or [])} material records) and checked published observations against their stored source contexts from downloaded PDFs/product pages."
    )
    lines.append(
        "I also spot-checked representative downloaded datasheets with PDF text extraction: Bambu PLA Sparkle, Anycubic PLA Silk, 3DXTech 3DXMAX ABS, 3DXTech Triton ABS, and Prusament PLA."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total issue records: {len(issues)}")
    lines.append(f"- Affected material/source records: {affected_materials}")
    lines.append(f"- Affected observation rows: {affected_observations}")
    lines.append(f"- High confidence: {by_conf['high']}")
    lines.append(f"- Medium confidence: {by_conf['medium']}")
    lines.append(f"- Uncertain/review: {by_conf['uncertain']}")
    lines.append("")
    lines.append("## Issue Classes")
    lines.append("")
    for (confidence, issue_type), count in sorted(by_type.items(), key=lambda x: ({"high": 0, "medium": 1, "uncertain": 2}.get(x[0][0], 9), -x[1], x[0][1])):
        lines.append(f"- **{confidence}** `{issue_type}`: {count}")
    lines.append("")
    lines.append("## High Confidence Findings")
    lines.append("")
    for issue_type, count in Counter(item.issue_type for item in issues if item.confidence == "high").most_common():
        examples = [item for item in issues if item.confidence == "high" and item.issue_type == issue_type][:8]
        lines.append(f"### `{issue_type}` ({count})")
        lines.append("")
        for item in examples:
            lines.append(
                f"- {item.supplier} / {item.product} / `{item.property_key}`: raw `{item.raw_value}` -> `{item.value_nominal}` {item.unit_raw}. {item.evidence}"
            )
            lines.append(f"  Source: `{item.source_file}`")
            lines.append(f"  Context: {short(item.source_context)}")
        if count > len(examples):
            lines.append(f"- ... {count - len(examples)} more in `{REPORT_CSV.name}`")
        lines.append("")
    lines.append("## Medium Confidence / User-Interpretation Risks")
    lines.append("")
    for issue_type, count in Counter(item.issue_type for item in issues if item.confidence == "medium").most_common():
        examples = [item for item in issues if item.confidence == "medium" and item.issue_type == issue_type][:8]
        lines.append(f"### `{issue_type}` ({count})")
        lines.append("")
        for item in examples:
            lines.append(
                f"- {item.supplier} / {item.product} / `{item.property_key}` raw `{item.raw_value}`: {item.evidence}"
            )
            lines.append(f"  Context: {short(item.source_context)}")
        if count > len(examples):
            lines.append(f"- ... {count - len(examples)} more in `{REPORT_CSV.name}`")
        lines.append("")
    lines.append("## Uncertain Review Queue")
    lines.append("")
    for issue_type, count in Counter(item.issue_type for item in issues if item.confidence == "uncertain").most_common():
        examples = [item for item in issues if item.confidence == "uncertain" and item.issue_type == issue_type][:10]
        lines.append(f"### `{issue_type}` ({count})")
        lines.append("")
        for item in examples:
            lines.append(
                f"- {item.supplier} / {item.product} / `{item.property_key}` raw `{item.raw_value}` -> `{item.value_nominal}` {item.unit_raw}. {item.evidence}"
            )
            lines.append(f"  Context: {short(item.source_context)}")
        if count > len(examples):
            lines.append(f"- ... {count - len(examples)} more in `{REPORT_CSV.name}`")
        lines.append("")
    lines.append("## Recommended Remediation Order")
    lines.append("")
    lines.append("1. Block standards-code captures (`ISO527`, `ISO178`, `ISO179`, `ISO306`, `ASTM D257`, etc.) in `candidate_raw_value`, including no-space variants.")
    lines.append("2. Make electrical extraction exponent-aware and store both mantissa/exponent and inequality/range semantics.")
    lines.append("3. Anchor values, methods, orientation, and conditions to the same table row/cell neighborhood instead of the entire context window.")
    lines.append("4. Treat `/`, `N/A`, `not applicable`, and `no break` as missing/categorical outcomes, never numeric chart values.")
    lines.append("5. Split impact observations by actual method and unit instead of mixing area-normalized `kJ/m2` data into an Izod `J/m` canonical slot.")
    lines.append("")
    lines.append(f"Full machine-readable outputs: `{REPORT_JSON.name}` and `{REPORT_CSV.name}`.")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ANALYSIS_DIR.mkdir(exist_ok=True)
    data = load_database()
    issues = detect_issues(data)
    payload = {
        "generated": "2026-06-07",
        "materials_count": len(data.get("materials") or []),
        "issue_count": len(issues),
        "counts_by_confidence": dict(Counter(item.confidence for item in issues)),
        "counts_by_type": {
            f"{confidence}:{issue_type}": count
            for (confidence, issue_type), count in Counter((item.confidence, item.issue_type) for item in issues).items()
        },
        "issues": [item.as_dict() for item in issues],
    }
    REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(issues)
    write_markdown(issues, data)
    print(f"Wrote {len(issues)} issues")
    print(REPORT_MD)
    print(REPORT_JSON)
    print(REPORT_CSV)


if __name__ == "__main__":
    main()
