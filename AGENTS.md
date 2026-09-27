# Local Agent Rules & Guidelines (Google Family Link & Home Assistant Add-ons)

## 1. Home Assistant Add-on Versioning Policy
- **Always bump version on changes**: Whenever modifying add-on code (`Dockerfile`, `config.yaml`, `run.sh`, `familylink_mqtt.py`, `familylink_ctl.py`), increment the `version:` field in `familylink/config.yaml` using SemVer (e.g. `1.0.1` -> `1.0.2`).
- Home Assistant Supervisor detects updates strictly via the `version:` tag in `config.yaml`. Without a bump, the UI will not show the update button.

## 2. Git & Commit Policy
- **Author Identity**: All commits in this repository must strictly be committed under:
  ```text
  Andy Simons <andy.a.simons@gmail.com>
  ```
- **Language**: Commit messages, comments, logs, and documentation must strictly be in **English**.
- **Conventional Commits**: Use conventional commit prefixes: `feat:`, `fix:`, `chore:`, `docs:`, `style:`.

## 3. Security & Sensitive Data Protection
- **Never commit credentials**: Never commit `cookies.json`, `credentials.json`, `*.token`, or raw session tokens (`SAPISID`, `1PSID`, `oauth_token`, `aas_et`).
- **Never commit personal IDs**: Do not hardcode real Google Account IDs (`userId`), Device MUD IDs, child names, or parent emails into public source code.
- **Randomized Identifiers**: Never use hardcoded/static default client IDs like `"0123456789abcdef"`. Always use crypto-randomized identifiers (`secrets.token_hex(8)`).

## 4. Reliability & Error Handling
- **Crash-proof Daemon**: The MQTT bridge must never enter a crash-loop on expired credentials (401/403). Instead:
  - Keep the process running and connected to MQTT.
  - Report the authentication problem via MQTT Discovery (`binary_sensor` with `device_class: problem`).
  - Periodically retry loading fresh credentials so user updates in UI take effect without manual container restart.
