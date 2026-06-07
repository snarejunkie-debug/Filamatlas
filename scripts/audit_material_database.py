from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_PATH = ROOT / "web" / "data" / "materials.json"

STRICT_RANGES: dict[str, tuple[float, float]] = {
    "density": (0.45, 2.6),
    "nozzle_temperature": (120, 480),
    "bed_temperature": (0, 170),
    "chamber_temperature": (0, 180),
    "drying_temperature": (20, 160),
    "impact_charpy": (0, 350),
    "impact_izod_area": (0, 350),
    "impact_strength": (0, 350),
    "tensile_modulus": (1, 30000),
    "flexural_modulus": (1, 30000),
}

DENSE_FILL_WORDS = (
    "bronze",
    "copper",
    "iron",
    "magnetic",
    "magnetite",
    "metal",
    "steel",
    "tungsten",
)


def load_database(path: Path | str = DEFAULT_JSON_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def as_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def material_text(material: dict[str, Any]) -> str:
    modifiers = " ".join(str(m) for m in material.get("modifiers") or [])
    return " ".join(
        str(material.get(key) or "")
        for key in ("supplier", "product", "base_material", "material_family", "source_file", "source_type")
    ) + f" {modifiers}"


def is_dense_filled(material: dict[str, Any]) -> bool:
    text = material_text(material).lower()
    return any(word in text for word in DENSE_FILL_WORDS)


def normalize_unit_context(text: str) -> str:
    cleaned = str(text or "").lower()
    cleaned = cleaned.replace("\u00b2", "2").replace("\u00b3", "3")
    cleaned = cleaned.replace("\u00c2\u00b2", "2").replace("\u00c2\u00b3", "3")
    cleaned = cleaned.replace(" ", "").replace("|", "")
    return cleaned


def quality_flags(observation: dict[str, Any]) -> set[str]:
    return {flag for flag in str(observation.get("quality_flag") or "").split(";") if flag}


def impact_method_family(text: str) -> str | None:
    if re.search(r"\bISO\s*[-/]?\s*179\b", text, re.I) or re.search(r"\bASTM\s*D\s*6110\b", text, re.I):
        return "charpy_area"
    if re.search(r"\bISO\s*[-/]?\s*180\b", text, re.I):
        return "iso_izod_area"
    if re.search(r"\bASTM\s*D\s*(?:256|4812)\b", text, re.I):
        return "astm_izod_linear"
    return None


def impact_unit_family(unit: str | None) -> str | None:
    if unit in {"kJ/m2", "J/m2"}:
        return "area"
    if unit in {"J/m", "ft-lb/in"}:
        return "linear"
    return None


def impact_label_text(observation: dict[str, Any]) -> str:
    return " ".join(str(observation.get(key) or "") for key in ("property_key", "property_label", "raw_label")).lower()


def iter_observations(data: dict[str, Any]):
    for material in data.get("materials") or []:
        for observation in material.get("observations") or []:
            yield material, observation


def issue(kind: str, message: str, material: dict[str, Any] | None = None, observation: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "kind": kind,
        "message": message,
        "supplier": material.get("supplier") if material else None,
        "product": material.get("product") if material else None,
        "source_file": material.get("source_file") if material else None,
        "property_key": observation.get("property_key") if observation else None,
        "raw_value": observation.get("raw_value") if observation else None,
        "value_nominal": observation.get("value_nominal") if observation else None,
        "source_context": observation.get("source_context") if observation else None,
    }


def observation_values(material: dict[str, Any], property_key: str) -> list[float]:
    values = []
    for observation in material.get("observations") or []:
        if observation.get("property_key") != property_key:
            continue
        value = as_number(observation.get("value_nominal"))
        if value is not None:
            values.append(value)
    return values


def matching_materials(data: dict[str, Any], *, supplier: str = "", product: str = "", source_file: str = "") -> list[dict[str, Any]]:
    supplier = supplier.lower()
    product = product.lower()
    source_file = source_file.lower()
    matches = []
    for material in data.get("materials") or []:
        if supplier and supplier not in str(material.get("supplier") or "").lower():
            continue
        if product and product not in str(material.get("product") or "").lower():
            continue
        if source_file and source_file not in str(material.get("source_file") or "").lower():
            continue
        matches.append(material)
    return matches


def check_source_paths(data: dict[str, Any]) -> list[dict[str, Any]]:
    problems = []
    for material in data.get("materials") or []:
        source_file = str(material.get("source_file") or "")
        if not source_file or re.match(r"https?://", source_file, re.I):
            continue
        if not (ROOT / source_file).exists():
            problems.append(issue("missing_source_path", f"Source path does not exist: {source_file}", material))
    return problems


def check_exponent_captures(data: dict[str, Any]) -> list[dict[str, Any]]:
    problems = []
    for material, observation in iter_observations(data):
        value = as_number(observation.get("value_nominal"))
        if value is None:
            continue
        raw = str(observation.get("raw_value") or "").strip().replace(",", ".")
        context = normalize_unit_context(observation.get("source_context") or "")
        prop = observation.get("property_key")
        if prop == "density" and abs(value - 3) < 1e-9 and "g/cm3" in context:
            problems.append(issue("unit_exponent_capture", "Density value appears to be the exponent in g/cm3.", material, observation))
        if prop in {"melt_volume_rate", "max_volumetric_speed"} and re.fullmatch(r"3(?:\.0+)?", raw):
            if "cm3" in context or "mm3" in context:
                problems.append(issue("unit_exponent_capture", f"{prop} value appears to be a cubic-unit exponent.", material, observation))
        if prop in {"impact_charpy", "impact_strength"} and re.fullmatch(r"2(?:\.0+)?", raw):
            if "kj/m2" in context or "j/m2" in context:
                problems.append(issue("unit_exponent_capture", f"{prop} value appears to be an area-unit exponent.", material, observation))
    return problems


def check_plausibility(data: dict[str, Any]) -> list[dict[str, Any]]:
    problems = []
    for material, observation in iter_observations(data):
        prop = observation.get("property_key")
        value = as_number(observation.get("value_nominal"))
        if prop not in STRICT_RANGES or value is None:
            continue
        lo, hi = STRICT_RANGES[prop]
        if prop == "density" and is_dense_filled(material):
            hi = 8.5
        if not (lo <= value <= hi):
            problems.append(
                issue(
                    "outside_strict_range",
                    f"{prop}={value:g} is outside strict range {lo:g}-{hi:g}.",
                    material,
                    observation,
                )
            )
    return problems


def check_impact_method_units(data: dict[str, Any]) -> list[dict[str, Any]]:
    problems = []
    impact_keys = {"impact_charpy", "impact_izod", "impact_izod_area", "impact_strength"}
    for material, observation in iter_observations(data):
        prop = observation.get("property_key")
        if prop not in impact_keys:
            continue
        flags = quality_flags(observation)
        if "unit_not_converted" in flags:
            problems.append(issue("impact_unit_not_converted", "Impact value has an unconverted unit.", material, observation))

        unit_canonical = observation.get("unit_canonical")
        unit_family = impact_unit_family(unit_canonical)
        if prop == "impact_izod" and unit_family != "linear":
            problems.append(issue("impact_key_unit_family_mismatch", "Linear Izod records must be stored in J/m.", material, observation))
        if prop in {"impact_charpy", "impact_izod_area", "impact_strength"} and unit_family != "area":
            problems.append(issue("impact_key_unit_family_mismatch", f"{prop} records must be stored in kJ/m2.", material, observation))

        method_text = " ".join(str(observation.get(key) or "") for key in ("test_method", "source_context"))
        method_family = impact_method_family(method_text)
        label_text = impact_label_text(observation)
        flagged_method_mismatch = any(flag.startswith("impact_method_unit_mismatch:") for flag in flags)
        if method_family == "astm_izod_linear" and prop != "impact_izod":
            if flagged_method_mismatch:
                continue
            problems.append(issue("impact_method_key_mismatch", "ASTM D256/D4812 Izod records should be stored under linear Izod.", material, observation))
        if method_family == "iso_izod_area" and prop != "impact_izod_area":
            if prop == "impact_charpy" and "charpy" in label_text:
                continue
            problems.append(issue("impact_method_key_mismatch", "ISO 180 Izod records should be stored under area-normalized Izod.", material, observation))
        if method_family == "charpy_area" and prop not in {"impact_charpy", "impact_strength"}:
            problems.append(issue("impact_method_key_mismatch", "ISO 179/ASTM D6110 records should be stored as Charpy/generic area impact.", material, observation))
    return problems


def check_golden_records(data: dict[str, Any]) -> list[dict[str, Any]]:
    problems = []
    for label, source_fragment in (
        ("Prusament PLA", "1_PLA_Prusament_TDS_2022_EN.pdf"),
        ("Prusament PLA Blend", "TDS_Prusament_PLA-Blend_EN.pdf"),
    ):
        matches = matching_materials(data, supplier="Prusa Polymers", source_file=source_fragment)
        if not matches:
            problems.append(issue("missing_golden_record", f"Missing golden Prusa source: {source_fragment}"))
            continue
        densities = [value for material in matches for value in observation_values(material, "density")]
        if not any(abs(value - 1.24) <= 0.005 for value in densities):
            problems.append(issue("golden_density_mismatch", f"{label} density should publish as 1.24 g/cm3; found {densities}.", matches[0]))
        if any(abs(value - 3) <= 0.005 for value in densities):
            problems.append(issue("golden_density_exponent", f"{label} still publishes 3 g/cm3.", matches[0]))

    build_series_pla = matching_materials(data, supplier="MatterHackers", product="Build Series PLA")
    for material in build_series_pla:
        densities = observation_values(material, "density")
        if any(abs(value - 3) <= 0.005 for value in densities):
            problems.append(issue("golden_density_exponent", "MatterHackers Build Series PLA still publishes 3 g/cm3.", material))
        if densities and not any(abs(value - 1.25) <= 0.02 for value in densities):
            problems.append(issue("golden_density_mismatch", f"MatterHackers Build Series PLA density should stay near 1.25 g/cm3; found {densities}.", material))

    for material in matching_materials(data, supplier="3DXTech", product="3DXMAX ABS"):
        nozzle = observation_values(material, "nozzle_temperature")
        bed = observation_values(material, "bed_temperature")
        if nozzle and any(value < 120 for value in nozzle):
            problems.append(issue("golden_nozzle_bed_mixup", f"3DXMAX ABS nozzle values include an implausibly low bed-like value: {nozzle}.", material))
        if bed and any(value > 170 for value in bed):
            problems.append(issue("golden_nozzle_bed_mixup", f"3DXMAX ABS bed values include a nozzle-like value: {bed}.", material))
    return problems


def collect_issues(data: dict[str, Any]) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    problems.extend(check_source_paths(data))
    problems.extend(check_exponent_captures(data))
    problems.extend(check_plausibility(data))
    problems.extend(check_impact_method_units(data))
    problems.extend(check_golden_records(data))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit generated filament material database for parser accuracy risks.")
    parser.add_argument("path", nargs="?", default=str(DEFAULT_JSON_PATH), help="Path to web/data/materials.json")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any audit issue is found.")
    parser.add_argument("--max-issues", type=int, default=50, help="Maximum issue details to print.")
    args = parser.parse_args(argv)

    data = load_database(args.path)
    problems = collect_issues(data)
    print(f"Audited {len(data.get('materials') or [])} material records; issues: {len(problems)}")
    for problem in problems[: args.max_issues]:
        location = " / ".join(str(problem.get(key) or "") for key in ("supplier", "product", "property_key") if problem.get(key))
        print(f"- [{problem['kind']}] {location}: {problem['message']}")
    if len(problems) > args.max_issues:
        print(f"... {len(problems) - args.max_issues} more issues omitted")
    return 1 if args.strict and problems else 0


if __name__ == "__main__":
    sys.exit(main())
