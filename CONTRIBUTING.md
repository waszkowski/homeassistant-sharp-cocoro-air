# Contributing

Thanks for your interest in improving this integration! This document covers the basics for getting started.

## Reporting bugs

Please open an issue on GitHub with:

- Your Home Assistant version
- Your Sharp device model (e.g. KI-TX75EU)
- The HACS version of this integration (e.g. `0.1.0`)
- Relevant log lines from Home Assistant — enable debug logging by adding the following to your `configuration.yaml`:

  ```yaml
  logger:
    default: warning
    logs:
      custom_components.sharp_cocoro_air: debug
  ```

  Restart Home Assistant, reproduce the issue, then attach the relevant log lines. **Redact your email, password, and any tokens before sharing.**

## Suggesting features

Open an issue describing the feature, why it would be useful, and (if possible) which Sharp/ECHONET property or mobile-app feature it corresponds to. Reverse-engineering pointers help a lot.

## Local development

The integration lives entirely under `custom_components/sharp_cocoro_air/`. To develop against a real Home Assistant instance:

1. Symlink or copy the directory into your HA config: `config/custom_components/sharp_cocoro_air`.
2. Restart Home Assistant after each code change (or use the Developer Tools → "Reload" actions where applicable).
3. Watch logs with debug enabled (see above).

## Pull requests

- Keep PRs focused — one logical change per PR.
- For non-trivial changes, please open an issue first to discuss the approach.
- Match the existing code style (Python 3.12+, type hints, `from __future__ import annotations`, async-first).
- If you add or change device behavior, please mention which device model you tested against.

## Code of conduct

Be kind, be patient. This is a community project maintained on volunteer time.
