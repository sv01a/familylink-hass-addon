# Google Family Link Bridge (Home Assistant Add-on)

A Home Assistant Add-on for **Supervised** and **OS** installations to manage child devices and monitor screen time via Google Family Link.

---

## Features

- 📊 **Daily Screen Time**: Monitor total daily screen time and individual device usage.
- 🎮 **Top Apps Breakdown**: Real-time list of most used apps and their durations saved in sensor attributes.
- 🔒 **Remote Screen Lock**: Switch to lock or unlock devices on demand.
- ⏳ **Bonus Time Management**: Buttons to add +15, +30, or +60 minutes, plus custom bonus duration input.
- 🔑 **Dual Authentication**: Permanent Master Token (OAuth) or Browser Cookies.
- 🚀 **MQTT Discovery**: Automatic entity creation in Home Assistant without manual YAML editing.

---

## Authentication Modes

### Mode 1: Master Token (Recommended, Permanent)
Generate a permanent Google Master Token using `tools/get_master_token.py` and configure:
- `google_email`: your parent Google account email.
- `master_token`: the token string (`aas_et/...`).
- `android_id`: the 16-hex Android ID from `credentials.json`.

### Mode 2: Browser Cookies (Fallback)
If you prefer cookies, leave `master_token` empty and provide:
- `cookies_text`: Google account cookies string.

---

## Configuration

In the **Configuration** tab of the add-on, provide:

| Field | Type | Description |
|---|---|---|
| `mqtt_host` | string | Hostname of your Mosquitto broker (default: `core-mosquitto`). |
| `mqtt_port` | port | MQTT port (default: `1883`). |
| `mqtt_user` | string | MQTT username (optional). |
| `mqtt_password` | password | MQTT password (optional). |
| `poll_interval` | int | Polling interval in seconds (default: `300` = 5 minutes). |
| `google_email` | string | Parent Google email for Master Token authentication. |
| `master_token` | password | Permanent Google Master Token (`aas_et/...`). |
| `android_id` | string | 16-hex Android client ID. |
| `cookies_text` | string | Fallback browser cookies. |
