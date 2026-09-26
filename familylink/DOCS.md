# Google Family Link Bridge (Home Assistant Add-on)

A Home Assistant Add-on for **Supervised** and **OS** installations to manage child devices and monitor screen time via Google Family Link.

---

## Features

- 📊 **Daily Screen Time**: Monitor total daily screen time and individual device usage.
- 🎮 **Top Apps Breakdown**: Real-time list of most used apps and their durations saved in sensor attributes.
- 🔒 **Remote Screen Lock**: Switch to lock or unlock devices on demand.
- ⏳ **Bonus Time Management**: Buttons to add +15, +30, or +60 minutes, plus custom bonus duration input.
- 🚀 **MQTT Discovery**: Automatic entity creation in Home Assistant without manual YAML editing.

---

## Installation

1. Add this repository to your **Add-on Store** repositories list.
2. Select **Google Family Link Bridge** and click **Install**.

---

## Configuration

In the **Configuration** tab of the add-on, provide:

- `mqtt_host`: Hostname or IP of your Mosquitto broker (default: `core-mosquitto`).
- `mqtt_port`: MQTT port (default: `1883`).
- `mqtt_user`: MQTT username (optional).
- `mqtt_password`: MQTT password (optional).
- `poll_interval`: Polling interval in seconds (default: `300` = 5 minutes).
- `cookies_text`: Google account cookies string (or contents of `cookies.json`).

Alternatively, you can place a `cookies.json` file inside your Home Assistant config directory:
```text
/config/familylink/cookies.json
```

---

## Entities Created in Home Assistant

For each child and supervised device:

| Entity Type | Entity ID Example | Description |
|---|---|---|
| Sensor | `sensor.<child>_screen_time_today` | Total daily screen time (minutes) + app list in attributes |
| Sensor | `sensor.<child>_<device>_time_today` | Screen time for the specific device (minutes) |
| Switch | `switch.<child>_<device>_lock` | Remotely lock (`ON`) or unlock (`OFF`) the device |
| Button | `button.<child>_<device>_15m` | Grant +15 minutes of bonus time |
| Button | `button.<child>_<device>_30m` | Grant +30 minutes of bonus time |
| Button | `button.<child>_<device>_60m` | Grant +60 minutes of bonus time |
| Number | `number.<child>_<device>_grant_bonus` | Enter custom bonus minutes (5 to 240) |
