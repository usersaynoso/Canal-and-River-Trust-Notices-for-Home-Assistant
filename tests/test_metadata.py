"""Metadata and translation tests for the CRT integration."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CRTMetadataTests(unittest.TestCase):
    """Validate the generated metadata files."""

    def test_manifest_matches_expected_basics(self) -> None:
        """Manifest should advertise the required HA metadata."""
        manifest = json.loads(
            (ROOT / "custom_components" / "crt_notices" / "manifest.json").read_text()
        )
        self.assertEqual(manifest["domain"], "crt_notices")
        self.assertEqual(manifest["name"], "Canal and River Trust Notices")
        self.assertEqual(manifest["iot_class"], "cloud_polling")
        self.assertEqual(manifest["integration_type"], "service")
        self.assertTrue(manifest["config_flow"])
        self.assertEqual(manifest["codeowners"], ["@usersaynoso"])
        self.assertIn("github.com/usersaynoso/Canal-and-River-Trust-Notices-for-Home-Assistant", manifest["documentation"])

    def test_hacs_metadata_enables_readme_rendering(self) -> None:
        """HACS metadata should be compatible with a custom component repo."""
        hacs = json.loads((ROOT / "hacs.json").read_text())
        self.assertEqual(hacs["name"], "Canal and River Trust Notices")
        self.assertEqual(hacs["homeassistant"], "2024.1.0")
        self.assertTrue(hacs["render_readme"])

    def test_strings_and_translations_match(self) -> None:
        """The English translation file should mirror strings.json."""
        strings = json.loads(
            (ROOT / "custom_components" / "crt_notices" / "strings.json").read_text()
        )
        translation = json.loads(
            (
                ROOT
                / "custom_components"
                / "crt_notices"
                / "translations"
                / "en.json"
            ).read_text()
        )
        self.assertEqual(strings, translation)

    def test_readme_and_workflows_exist_for_hacs_submission(self) -> None:
        """Repo should include the expected docs and CI files for HACS review."""
        readme = (ROOT / "README.md").read_text()
        self.assertIn("# Canal and River Trust Notices", readme)
        self.assertTrue((ROOT / ".github" / "workflows" / "hacs.yml").exists())
        self.assertTrue((ROOT / ".github" / "workflows" / "hassfest.yml").exists())
        self.assertTrue((ROOT / "LICENSE").exists())
        self.assertTrue(
            (ROOT / "custom_components" / "crt_notices" / "brand" / "icon.png").exists()
        )


if __name__ == "__main__":
    unittest.main()
