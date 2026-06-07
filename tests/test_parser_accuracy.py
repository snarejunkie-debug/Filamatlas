from __future__ import annotations

import unittest

from scripts import build_material_database as builder


def observations_for(rows: list[str]):
    builder.AUDIT_REJECTIONS.clear()
    builder.AUDIT_REJECTION_KEYS.clear()
    return builder.extract_observations(
        "",
        rows,
        source={
            "supplier": "fixture",
            "product": "fixture material",
            "source_type": "fixture",
            "source_file": "fixture",
        },
    )


def values(observations: list[dict], property_key: str) -> list[float]:
    return [
        observation["value_nominal"]
        for observation in observations
        if observation["property_key"] == property_key and observation["value_nominal"] is not None
    ]


class ParserAccuracyTest(unittest.TestCase):
    def test_prusament_pla_density_rejects_unit_exponent(self) -> None:
        rows = [
            "MVR [cm | 3/10 min](1) | 8-10 | ISO 1133 | Density [g/cm | 3] | 1.24 | ISO 1183 | Moisture Absorption in 24 hours [%](2) | 0.13 | Internal method"
        ]
        observations = observations_for(rows)

        self.assertEqual([1.24], values(observations, "density"))
        self.assertEqual([9.0], values(observations, "melt_volume_rate"))
        self.assertEqual([0.13], values(observations, "water_absorption"))
        self.assertNotIn(3.0, values(observations, "density"))
        self.assertNotIn(24.0, values(observations, "water_absorption"))
        self.assertTrue(any(row["reason"] == "unit_exponent_or_footnote" for row in builder.AUDIT_REJECTIONS))

    def test_prusament_pla_blend_density_rejects_split_cubic_unit(self) -> None:
        rows = [
            "MFR [g/10 min](1) | 9-11 | ISO 1133 | MVR [cm | 3/10 min](1) | 8-10 | ISO 1133 | Density [g/cm | 3] | 1.24 | ISO 1183"
        ]
        observations = observations_for(rows)

        self.assertEqual([1.24], values(observations, "density"))
        self.assertNotIn(3.0, values(observations, "density"))

    def test_3dxtech_nozzle_and_bed_temperatures_do_not_cross_capture(self) -> None:
        rows = [
            "Printer: Open Source FDM/FFF | Nozzle: 0.4mm | Layer Height: 0.25mm | Infill: 100%, +/- 45° | Extrusion Temp: 225°C | Bed Temp: 110°C"
        ]
        observations = observations_for(rows)

        self.assertEqual([225.0], values(observations, "nozzle_temperature"))
        self.assertEqual([110.0], values(observations, "bed_temperature"))

    def test_matterhackers_html_density_and_length_are_separate(self) -> None:
        rows = [
            "Density | 1.25 g/cm3 | official_html_specs",
            "Filament Length | 332.60 m | official_html_specs",
            "Charpy Impact Strength | Length: 332.60 m | official_html_specs",
        ]
        observations = observations_for(rows)

        self.assertEqual([1.25], values(observations, "density"))
        self.assertNotIn(3.0, values(observations, "density"))
        self.assertEqual([], values(observations, "impact_charpy"))

    def test_charpy_context_does_not_inherit_neighboring_izod_method(self) -> None:
        rows = [
            "23 C, notched | 10 kJ/m2 | ISO 180-1A | -30 C, notched | Charpy impact strength | 25 kJ/m2"
        ]
        observations = observations_for(rows)
        charpy = [o for o in observations if o["property_key"] == "impact_charpy"]

        self.assertEqual([25.0], values(observations, "impact_charpy"))
        self.assertTrue(charpy)
        self.assertNotIn("ISO 180", charpy[0]["source_context"])
        self.assertIsNone(charpy[0]["test_method"])

    def test_impact_method_unit_conflict_is_rejected(self) -> None:
        rows = [
            "ASTM D790 | 1.27 mm/min | Izod impact strength | 5 kJ/m2 | ASTM D256 | 23 C, notched"
        ]
        observations = observations_for(rows)

        self.assertEqual([], values(observations, "impact_izod"))
        self.assertEqual([], values(observations, "impact_izod_area"))
        self.assertTrue(any(row["reason"] == "impact_method_unit_mismatch" for row in builder.AUDIT_REJECTIONS))

    def test_astm_izod_ft_lbf_per_in_converts_to_metric_j_per_m(self) -> None:
        rows = ["Notched Izod Impact | ASTM D256 | ft-lb/in | 0.3"]
        observations = observations_for(rows)
        impact = [row for row in observations if row["property_key"] == "impact_izod"]

        self.assertEqual(1, len(impact))
        self.assertEqual("ft-lb/in", impact[0]["unit_raw"])
        self.assertEqual("J/m", impact[0]["unit_canonical"])
        self.assertAlmostEqual(0.3 * builder.FT_LBF_PER_IN_TO_J_PER_M, impact[0]["value_nominal"], places=4)
        self.assertIn("unit_converted:ft-lb/in->J/m", impact[0]["quality_flag"])

    def test_split_ft_lbf_per_in_row_recovers_astm_izod_value(self) -> None:
        rows = ["0.3 ft-lb/in | ASTM D638 | ASTM D638 | ASTM D638 | ASTM D256 | Diameter 1.75mm"]
        observations = observations_for(rows)
        impact = [row for row in observations if row["property_key"] == "impact_izod"]
        diameters = [row for row in observations if row["property_key"] == "diameter"]

        self.assertEqual(1, len(impact))
        self.assertAlmostEqual(0.3 * builder.FT_LBF_PER_IN_TO_J_PER_M, impact[0]["value_nominal"], places=4)
        self.assertEqual("ASTM D256", impact[0]["test_method"])
        self.assertIn("unit_converted:ft-lb/in->J/m", impact[0]["quality_flag"])
        self.assertTrue(all(row["unit_raw"] == "mm" for row in diameters))

    def test_iso_izod_area_normalized_values_stay_in_area_bucket(self) -> None:
        rows = ["Izod Impact Strength | ISO 180/A | kJ/m2 | 8"]
        observations = observations_for(rows)
        impact = [row for row in observations if row["property_key"] == "impact_izod_area"]

        self.assertEqual(1, len(impact))
        self.assertEqual("kJ/m2", impact[0]["unit_raw"])
        self.assertEqual("kJ/m2", impact[0]["unit_canonical"])
        self.assertEqual(8.0, impact[0]["value_nominal"])
        self.assertIn("impact_area_normalized", impact[0]["quality_flag"])
        self.assertNotIn("unit_not_converted", impact[0]["quality_flag"])

    def test_iso179_row_labeled_izod_routes_to_charpy_with_quality_note(self) -> None:
        rows = ["Izod Impact Strength (kJ/m2) (X-Y) | ISO 179 | kJ/m2 | 40"]
        observations = observations_for(rows)
        charpy = [row for row in observations if row["property_key"] == "impact_charpy"]

        self.assertEqual(1, len(charpy))
        self.assertEqual("kJ/m2", charpy[0]["unit_canonical"])
        self.assertEqual(40.0, charpy[0]["value_nominal"])
        self.assertIn("source_label_mismatch:izod_label_iso179", charpy[0]["quality_flag"])


if __name__ == "__main__":
    unittest.main()
