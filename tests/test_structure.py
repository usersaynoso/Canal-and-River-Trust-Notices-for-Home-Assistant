"""Static structure checks for code paths tied to live HA issues."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CRTStructureTests(unittest.TestCase):
    """Validate source-level expectations for recent regressions."""

    def test_config_flow_uses_plain_selector_options(self) -> None:
        """The config flow should avoid SelectOptionDict for wider HA compatibility."""
        config_flow = (
            ROOT / "custom_components" / "crt_notices" / "config_flow.py"
        ).read_text()
        self.assertNotIn("SelectOptionDict", config_flow)
        self.assertNotIn("self.config_entry =", config_flow)
        self.assertIn('"value": MODE_GPS', config_flow)
        self.assertIn(
            '"label": "GPS Proximity (Dynamic) or Home Assistant home coordinates"',
            config_flow,
        )
        self.assertIn("def _build_entity_selector_key", config_flow)
        self.assertNotIn("default=None", config_flow)
        self.assertIn("SelectSelectorMode.LIST", config_flow)

    def test_sensor_platform_exposes_individual_notice_entities(self) -> None:
        """Each matched notice should get its own entity in addition to summary sensors."""
        sensor_source = (
            ROOT / "custom_components" / "crt_notices" / "sensor.py"
        ).read_text()
        self.assertIn("CRTLastUpdatedSensor", sensor_source)
        self.assertIn("last_updated", sensor_source)
        self.assertIn("SensorDeviceClass.TIMESTAMP", sensor_source)
        self.assertIn("class CRTActiveNoticeSensor", sensor_source)
        self.assertIn("coordinator.async_add_listener", sensor_source)
        self.assertIn('notice_{notice_id}', sensor_source)
        self.assertIn("_remove_stale_notice_registry_entries", sensor_source)
        self.assertIn("entity_registry.async_remove", sensor_source)
        self.assertIn("EntityCategory.DIAGNOSTIC", sensor_source)
        self.assertIn("self.coordinator.data.last_updated", sensor_source)

    def test_binary_sensor_uses_diagnostic_category(self) -> None:
        """Summary/problem status should live in HA's diagnostic grouping."""
        binary_sensor_source = (
            ROOT / "custom_components" / "crt_notices" / "binary_sensor.py"
        ).read_text()
        self.assertIn("EntityCategory.DIAGNOSTIC", binary_sensor_source)

    def test_init_declares_config_entry_only_schema(self) -> None:
        """Hassfest expects config-entry-only integrations to declare this explicitly."""
        init_source = (
            ROOT / "custom_components" / "crt_notices" / "__init__.py"
        ).read_text()
        self.assertIn("cv.config_entry_only_config_schema(DOMAIN)", init_source)
        self.assertIn("last_updated: datetime", init_source)
        self.assertIn("last_updated=dt_util.utcnow()", init_source)


if __name__ == "__main__":
    unittest.main()
