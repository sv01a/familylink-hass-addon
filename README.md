# 🏠 Home Assistant Add-ons Repository

A custom Home Assistant Add-on repository for **Home Assistant OS** and **Supervised**.

---

## 📦 Add-ons in this repository

### 👨‍👩‍👧 [Google Family Link Bridge](./familylink)

An MQTT bridge for **Google Family Link** integration with automatic **Home Assistant MQTT Discovery**:

- 📊 **Daily Screen Time Monitoring**: Total daily screen time and individual tracking per child's device.
- 🎮 **Top Applications Usage**: Breakdown of used apps with duration stored in sensor attributes.
- 🔒 **Instant Device Screen Lock / Unlock**: Toggle switches (`switch`) to remotely lock and unlock devices.
- ⏳ **Bonus Time Management**: Quick action buttons (`+15m`, `+30m`, `+60m`) and custom duration number input (`number`).
- 🔑 **Permanent Authentication**: Long-lived Google Master Token (`aas_et/...`) support via Google Play Services OAuth flow.
- 🚀 **Zero-Config Entities**: Automatically registers devices, sensors, buttons, and switches in Home Assistant via MQTT Discovery without touching `configuration.yaml`.

---

## 🔑 Authentication (Permanent Master Token)

Browser session cookies expire quickly due to Google session binding. For a **permanent** set-and-forget setup, generate a **Google Master Token (`aas_et/...`)** using the included helper script:

👉 **[Master Token Generator Guide & Instructions](./tools/README.md)**

---

## 🛠 Installation

1. In Home Assistant web interface, navigate to **Settings** → **Add-ons** → **Add-on Store** (button in bottom-right).
2. Click the three dots menu (**⋮**) in top right corner → select **Repositories**.
3. Paste the URL of this repository:
   ```text
   https://github.com/sv01a/familylink-hass-addon
   ```
4. Click **Add**, then close the dialog.
5. Search or scroll to find **Google Family Link Bridge** → click **Install**.

---

## ⚙️ Configuration

Open the **Configuration** tab of the add-on:

| Option | Default | Description |
|---|---|---|
| `mqtt_host` | `core-mosquitto` | Hostname or IP of your MQTT broker (`core-mosquitto` if using official Mosquitto add-on) |
| `mqtt_port` | `1883` | MQTT port |
| `mqtt_user` | `""` | MQTT username (optional) |
| `mqtt_password` | `""` | MQTT password (optional) |
| `poll_interval` | `300` | Polling interval in seconds (default is 5 minutes) |
| `google_email` | `""` | Parent Google email for Master Token authentication |
| `master_token` | `""` | Permanent Master Token (`aas_et/...`) |
| `android_id` | `""` | 16-hex Android client ID from `credentials.json` |

---

## 📱 How to Use in Home Assistant

Once started, the add-on uses **MQTT Discovery** to automatically populate your Home Assistant.

### 1. View Devices & Entities
Go to **Settings** → **Devices & services** → **MQTT**:
- **`sensor.<child>_screen_time_today`**: Total screen time today (in minutes). Contains formatted time (`formatted_time`) and `top_apps` in attributes.
- **`sensor.<child>_<device>_time_today`**: Screen time for specific device.
- **`switch.<child>_<device>_lock`**: Turn ON to lock device, OFF to unlock.
- **`button.<child>_<device>_15m` / `30m` / `60m`**: Press to grant bonus time.
- **`number.<child>_<device>_grant_bonus`**: Enter custom minutes.

### 2. Dashboard Card Examples

#### Entities Card
```yaml
type: entities
title: "👧 Sofia Devices"
entities:
  - entity: sensor.sofia_screen_time_today
    name: "Total Screen Time"
  - entity: sensor.sofia_tablet_time_today
    name: "Tablet Usage"
  - entity: switch.sofia_tablet_lock
    name: "Lock Tablet"
  - entity: button.sofia_tablet_30m
    name: "Grant +30 min"
```

#### Top Apps Breakdown (Markdown Card)
```yaml
type: markdown
title: "🎮 Top Apps Today"
content: >
  **Total:** {{ state_attr('sensor.sofia_screen_time_today', 'formatted_time') }}

  {% for app in state_attr('sensor.sofia_screen_time_today', 'top_apps') %}
    - **{{ app.title }}**: {{ app.minutes }} min
  {% endfor %}
```
