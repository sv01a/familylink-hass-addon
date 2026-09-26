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
- 🚀 **Zero-Config Entities**: Automatically registers devices, sensors, buttons, and switches in Home Assistant via MQTT Discovery without touching `configuration.yaml`.

---

## 🛠 Installation

1. In Home Assistant web interface, navigate to **Settings** → **Add-ons** → **Add-on Store** (button in the bottom-right corner).
2. Click the three dots menu (**⋮**) in the top right corner → select **Repositories**.
3. Paste the URL of your GitHub repository:
   ```text
   https://github.com/sv01a/familylink-hass-addon
   ```
4. Click **Add**, then close the dialog.
5. The store will refresh, and **Google Family Link Bridge** will appear under your custom repository section.
6. Click on the add-on → click **Install**.

---

## ⚙️ Configuration

Open the **Configuration** tab of the add-on and specify:

| Option | Default | Description |
|---|---|---|
| `mqtt_host` | `core-mosquitto` | Hostname or IP of your MQTT broker (`core-mosquitto` if using official Mosquitto add-on) |
| `mqtt_port` | `1883` | MQTT port |
| `mqtt_user` | `""` | MQTT username (optional) |
| `mqtt_password` | `""` | MQTT password (optional) |
| `poll_interval` | `300` | Polling interval in seconds (default is 5 minutes) |
| `cookies_text` | `""` | Google session cookies (paste raw cookie string or contents of `cookies.json`) |

---

## 🚀 Starting the Add-on

1. Save the configuration.
2. Return to the **Info** tab.
3. Enable **Start on boot** and **Watchdog**.
4. Click **Start**.
5. Check the **Log** tab to verify connection to MQTT and discovery of your children's devices.
