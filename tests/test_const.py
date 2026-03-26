"""Unit tests for pure CRT notice helper logic."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONST_PATH = ROOT / "custom_components" / "crt_notices" / "const.py"

SPEC = importlib.util.spec_from_file_location("crt_notices_const", CONST_PATH)
const = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(const)


class CRTConstTests(unittest.TestCase):
    """Validate helper behavior without a Home Assistant runtime."""

    def test_waterways_match_verified_source_count(self) -> None:
        """The embedded waterway list should contain the full CRT page source."""
        self.assertEqual(len(const.WATERWAYS), 200)

    def test_waterway_entries_include_expected_examples(self) -> None:
        """Specific entries from the CRT source should be preserved."""
        names_by_code = {item["value"]: item["name"] for item in const.WATERWAYS}
        self.assertEqual(names_by_code["GU"], "Grand Union Canal")
        self.assertEqual(names_by_code["GU-GL"], "Leicester Line")
        self.assertEqual(names_by_code["BBN-LI-LB"], "Limehouse Basin")

    def test_build_entry_title_for_gps_mode(self) -> None:
        """GPS titles should include the configured radius."""
        self.assertEqual(
            const.build_entry_title(const.MODE_GPS, radius_miles=25),
            "Canal and River Trust Notices (GPS - 25mi)",
        )

    def test_build_entry_title_for_manual_mode(self) -> None:
        """Manual titles should use the selected waterway names."""
        self.assertEqual(
            const.build_entry_title(const.MODE_MANUAL, selected_waterways=["GU"]),
            "Canal and River Trust Notices (Grand Union Canal)",
        )
        self.assertEqual(
            const.build_entry_title(
                const.MODE_MANUAL,
                selected_waterways=["GU", "TM"],
            ),
            "Canal and River Trust Notices (Grand Union Canal +1)",
        )

    def test_matches_selected_waterways_uses_substring_logic(self) -> None:
        """Parent and branch naming should work with substring matching."""
        self.assertTrue(
            const.matches_selected_waterways(
                "Leicester Line (Grand Union Canal)",
                ["Grand Union Canal"],
            )
        )
        self.assertTrue(
            const.matches_selected_waterways(
                "Shropshire Union Canal, Trent & Mersey Canal",
                ["Trent & Mersey Canal"],
            )
        )
        self.assertFalse(
            const.matches_selected_waterways(
                "Oxford Canal",
                ["Grand Union Canal"],
            )
        )

    def test_extract_geometry_points_handles_geometry_collection(self) -> None:
        """GeoJSON point extraction should convert lon/lat to lat/lon pairs."""
        geometry = {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "Point", "coordinates": [-2.2029, 52.4823]},
                {"type": "Point", "coordinates": [-2.5, 52.1]},
            ],
        }
        self.assertEqual(
            const.extract_geometry_points(geometry),
            [(52.4823, -2.2029), (52.1, -2.5)],
        )
        self.assertEqual(const.extract_geometry_points({"type": "Point"}), [])

    def test_haversine_miles_returns_reasonable_result(self) -> None:
        """Distance calculations should be stable for nearby points."""
        distance = const.haversine_miles(52.4823, -2.2029, 52.5, -2.22)
        self.assertGreater(distance, 1.0)
        self.assertLess(distance, 2.0)

    def test_format_notice_brief_includes_key_fields(self) -> None:
        """Flattened notice text should stay readable in HA attributes."""
        self.assertEqual(
            const.format_notice_brief(
                title="Limehouse Lock Walkway Closed",
                waterway="Lee Navigation",
                type_name="Towpath Closure",
                start_date="2026-03-26T09:00:00+00:00",
                end_date=None,
            ),
            "Limehouse Lock Walkway Closed | Lee Navigation | Towpath Closure | "
            "2026-03-26T09:00:00+00:00 to Ongoing",
        )


if __name__ == "__main__":
    unittest.main()
