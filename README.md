# Canal and River Trust Notices

Home Assistant custom integration for live Canal & River Trust navigation notices.

This integration polls the public CRT notices API and creates Home Assistant entities for:

- blocking or restrictive navigation notices
- the nearest matching notice
- the total count of matching notices
- each active matching notice as its own sensor entity

## Features

- GPS proximity mode using a `device_tracker`, with automatic fallback to Home Assistant home coordinates
- Manual waterway selection mode using the embedded CRT waterway list
- Configurable radius, lookahead window, and polling interval
- Per-notice entities grouped under a single Home Assistant device
- HACS-compatible metadata and translations

## Installation

### HACS

1. Open HACS.
2. Go to `Integrations`.
3. Open the three-dot menu and choose `Custom repositories`.
4. Add `https://github.com/usersaynoso/Canal-and-River-Trust-Notices-for-Home-Assistant` as an `Integration`.
5. Install `Canal and River Trust Notices`.
6. Restart Home Assistant.

Or use My Home Assistant:

[![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=usersaynoso&repository=Canal-and-River-Trust-Notices-for-Home-Assistant&category=integration)

### Manual

1. Copy `custom_components/crt_notices` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Configuration

Add the integration from `Settings` -> `Devices & Services` -> `Add Integration`.

Two setup modes are available:

- `GPS Proximity (Dynamic) or Home Assistant home coordinates`
- `Manual Canal Selection (Static)`

If no tracker is selected, or if the tracker has no usable coordinates, the integration uses the Home Assistant home latitude and longitude.

## Entities

The integration creates:

- one binary sensor for blocking or restrictive navigation notices
- one summary sensor for the nearest notice
- one summary sensor for the notice count
- one sensor per active matching notice

## Data source

- [Canal & River Trust Notices](https://canalrivertrust.org.uk/notices)
- [CRT Notices API](https://canalrivertrust.org.uk/api/stoppage/notices)

## Development

Local verification:

```bash
python3 -m py_compile $(find custom_components -name '*.py' | sort)
python3 -m unittest discover -s tests -v
```
