from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts import audit_material_database as audit


ROOT = Path(__file__).resolve().parents[1]
MATERIALS_JSON = ROOT / "web" / "data" / "materials.json"
AUDIT_JSON = ROOT / "analysis" / "material_database_audit.json"


class DatabaseAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = audit.load_database(MATERIALS_JSON)

    def test_strict_audit_has_no_published_accuracy_issues(self) -> None:
        issues = audit.collect_issues(self.data)
        preview = "\n".join(f"{row['kind']}: {row['message']}" for row in issues[:10])
        self.assertEqual([], issues, preview)

    def test_prusament_density_golden_records(self) -> None:
        for source_fragment in ("1_PLA_Prusament_TDS_2022_EN.pdf", "TDS_Prusament_PLA-Blend_EN.pdf"):
            matches = audit.matching_materials(self.data, supplier="Prusa Polymers", source_file=source_fragment)
            self.assertTrue(matches, source_fragment)
            densities = [value for material in matches for value in audit.observation_values(material, "density")]
            self.assertTrue(any(abs(value - 1.24) <= 0.005 for value in densities), densities)
            self.assertFalse(any(abs(value - 3.0) <= 0.005 for value in densities), densities)

    def test_audit_report_records_rejected_candidates(self) -> None:
        if not AUDIT_JSON.exists():
            self.skipTest(f"generated audit artifact is not present: {AUDIT_JSON}")
        payload = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
        rejections = payload.get("rejections") or []
        self.assertGreater(len(rejections), 0)
        self.assertTrue(
            any(row.get("reason") == "unit_exponent_or_footnote" for row in rejections),
            "audit report should expose rejected exponent/footnote candidates",
        )


if __name__ == "__main__":
    unittest.main()
