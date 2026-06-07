from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "web" / "app.js"


class WebUnitFormattingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = APP_JS.read_text(encoding="utf-8")
        match = re.search(r"function formatUnit\(unit\) \{(?P<body>.*?)\n\}", cls.source, re.S)
        assert match is not None, "formatUnit(unit) must exist"
        cls.formatter_body = match.group("body")

    def test_formatter_has_scientific_symbols(self) -> None:
        for expected in ("°C", "g/cm³", "cm³/10 min", "mm³/s", "kJ/m²", "J/m²", "Ω", "Ω/sq"):
            self.assertIn(expected, self.formatter_body)

    def test_visible_unit_calls_use_formatter(self) -> None:
        for needle in ("canonical_unit", "unit_canonical", "stat.unit"):
            self.assertIn(needle, self.source)
        self.assertGreaterEqual(self.source.count("formatUnit("), 8)

    def test_formatter_outputs_do_not_use_ascii_science_units(self) -> None:
        output_literals = re.findall(r":\s*\"([^\"]+)\"", self.formatter_body)
        forbidden = {"degC", "cm3", "mm3", "kJ/m2", "J/m2", "ohm", "ohm/sq"}
        self.assertTrue(output_literals)
        self.assertFalse(forbidden.intersection(output_literals))

    def test_converted_values_have_marker_helpers(self) -> None:
        for needle in ("unit_converted:", "unitMarker", "conversionNotes", "unit-marker"):
            self.assertIn(needle, self.source)


if __name__ == "__main__":
    unittest.main()
