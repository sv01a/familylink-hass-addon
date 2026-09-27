# 🏠 Home Assistant Add-ons Repository

A custom Home Assistant Add-on repository for **Home Assistant OS** and **Supervised**.

---

## 📦 Add-ons in this repository

### 👨‍👩‍👧 [Google Family Link Bridge](./familylink)

An MQTT bridge for **Google Family Link** integration with automatic **Home Assistant MQTT Discovery**:

- 📊 **Daily Screen Time Monitoring**: Total daily screen time and individual tracking per child's device.
- ⏳ **Remaining Time & Live Quotas**: Direct API reading of remaining daily minutes and active bonus duration per device.
- 🔒 **Screen Lock Status**: Real-time binary sensor (`binary_sensor`) showing whether the device is currently locked.
- 🎮 **Top Applications Usage**: Breakdown of used apps with duration stored in sensor attributes.
- 🛑 **Remote Screen Lock**: Toggle switch (`switch`) to remotely lock/unlock screens.
- 🎁 **Safe Two-Step Bonus**: Number input (`number`) to choose duration (30 min default) + dedicated confirm button (`button`) to apply.
- 🔑 **Permanent Authentication**: Long-lived Google Master Token (`aas_et/...`) support via Google Play Services OAuth flow.
- 🚀 **Zero-Config Entities**: Automatically registers devices, sensors, and switches in Home Assistant via MQTT Discovery without touching `configuration.yaml`.

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

### Entities per Device:
- **`sensor.<child>_screen_time_today`**: Total screen time spent today (min).
- **`sensor.<child>_<device>_time_today`**: Time spent on this device today (min).
- **`sensor.<child>_<device>_remaining_time`**: Remaining regular daily quota (min).
- **`sensor.<child>_<device>_bonus_remaining`**: Remaining active bonus minutes.
- **`binary_sensor.<child>_<device>_locked`**: Whether the device is locked (`on` = locked).
- **`switch.<child>_<device>_lock`**: Turn ON to lock device, OFF to unlock.
- **`number.<child>_<device>_bonus_duration`**: Choose bonus duration (default 30 min, does NOT grant yet).
- **`button.<child>_<device>_grant_bonus`**: Click to grant the configured duration to the device.
