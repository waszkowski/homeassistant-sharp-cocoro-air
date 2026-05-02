# Sharp Cocoro Air — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Unofficial Home Assistant integration for **Sharp Cocoro Air** humidifying air purifiers via the cloud API used by the Sharp Life AIR mobile app.

> **Disclaimer:** This is an unofficial, community-maintained integration. It is **not affiliated with, endorsed by, or supported by Sharp Corporation**. Use at your own risk. The integration may break at any time if Sharp changes their cloud API.

## Features

- **Sensors** — temperature, humidity, fine particles, air quality index, odor level, dust level, overall dirt level, water tank status, light detection, fault status, current operation mode, humidification status, filter remaining life (HEPA, deodorizing, humidifying, ion, plasmacluster).
- **Fan entity** — turn on/off, switch operation modes (auto, silent, medium, high, night, pollen, AI auto, powerful).
- **Switch entity** — toggle humidification on/off.
- **Cloud polling** every 5 minutes by default (configurable).
- **Multi-device** — supports multiple paired purifiers in a single account.

## Region support

| Region | Status |
|---|---|
| Europe (EU) | ✅ Supported |
| Japan (JP) | ⏳ Planned |
| Taiwan (TW) | ⏳ Planned |

Currently only the EU Cocoro Air cloud (`auth-eu.global.sharp` / `eu-hms.cloudlabs.sharp.co.jp`) is implemented. Support for JP/TW regions is planned for a future release — contributions welcome.

## Tested devices

- **Sharp KI-TX75EU** (humidifying air purifier, EU)

Other EU Cocoro Air devices that work with the Sharp Life AIR mobile app should also work — please open an issue with your model if you successfully use the integration with another device, so it can be added here.

## Installation

### Via HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=waszkowski&repository=homeassistant-sharp-cocoro-air&category=integration)

This integration is not yet in the default HACS store. Click the badge above to open it directly in your Home Assistant, or add it manually as a custom repository:

1. Open HACS in Home Assistant.
2. Go to **Integrations** → top-right menu → **Custom repositories**.
3. Add `https://github.com/waszkowski/homeassistant-sharp-cocoro-air` as type **Integration**.
4. Search for *Sharp Cocoro Air* in HACS and install.
5. Restart Home Assistant.

### Manual installation

1. Copy `custom_components/sharp_cocoro_air/` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

After installation, add the integration via **Settings → Devices & Services → Add Integration** and search for *Sharp Cocoro Air*. You will be asked for:

- **Email** — the email address used in the Sharp Life AIR mobile app
- **Password** — your Sharp Life AIR account password

Credentials are stored in Home Assistant's encrypted config entry storage and are only sent to Sharp's official auth endpoint.

### Options

You can adjust the polling interval (in minutes) via the integration's **Configure** button. Minimum is 1 minute, default is 5 minutes.

## Known limitations

- **Cloud-only.** All communication goes through Sharp's cloud — there is no local control. If Sharp's servers are down, the integration cannot reach the device.
- **Polling, not push.** State updates arrive on the polling interval, not in real time.
- **Single account session.** Sharp's API uses a session-cookie pattern; the integration handles re-authentication automatically when the session expires, but rapid control commands during an expiry window may briefly fail before retrying.
- **No device-side telemetry beyond what the mobile app exposes.** Sensor values and modes mirror what is decoded from the ECHONET Lite properties returned by the cloud API.

## Contributing

Bug reports and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © waszkowski

## Acknowledgements

This integration was built by reverse-engineering the Sharp Life AIR mobile app and observing the cloud API traffic. It would not exist without the prior work of the open-source ECHONET Lite community and similar Sharp/Cocoro integrations in other smart-home ecosystems.
