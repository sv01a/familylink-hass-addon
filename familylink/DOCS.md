# Google Family Link Bridge (Home Assistant Add-on)

A Home Assistant Add-on for **Supervised** and **OS** installations to manage child devices and monitor screen time via Google Family Link.

---

## 🚀 How It Works (Zero Configuration in Lovelace)

Once the add-on starts and connects to your MQTT broker, **Home Assistant MQTT Discovery automatically creates all devices and entities**. You do **not** need to edit `configuration.yaml` or restart Home Assistant.

---

## 📱 Where to Find Your Devices in Home Assistant

1. Open Home Assistant web UI.
2. Go to **Settings** → **Devices & services** → **MQTT** integration card.
3. Click on **Devices** (or **Entities**).
4. You will see:
   - **`Family Link (<Child Name>)`**: Master child device with total screen time.
   - **`<Child Name> <Device Name>`**: One device per supervised hardware (e.g. tablet, phone).

---

## 📊 Monitoring Screen Time

### 1. Daily Total Screen Time Sensor
- **Entity ID**: `sensor.<child_name>_screen_time_today`
- **State**: Total screen time today in **minutes** (e.g. `185`).
- **Attributes**:
  - `formatted_time`: Human-readable format (e.g. `3h 5m`).
  - `date`: Current date (`YYYY-MM-DD`).
  - `top_apps`: Array of applications with minutes spent, e.g.:
    ```json
    [
      {"title": "MAX", "minutes": 80},
      {"title": "Likee", "minutes": 61},
      {"title": "Roblox", "minutes": 32}
    ]
    ```

### 2. Per-Device Screen Time Sensor
- **Entity ID**: `sensor.<child_name>_<device_name>_time_today`
- **State**: Time spent specifically on that tablet or phone today (in minutes).

---

## 🔒 Controlling Devices

For each supervised phone or tablet:

### 1. Screen Lock / Unlock Switch
- **Entity ID**: `switch.<child_name>_<device_name>_lock`
- Turn **ON**: Instantly locks the child's screen.
- Turn **OFF**: Unlocks the device screen.

### 2. Quick Bonus Buttons
- `button.<child_name>_<device_name>_15m` (+15 minutes)
- `button.<child_name>_<device_name>_30m` (+30 minutes)
- `button.<child_name>_<device_name>_60m` (+60 minutes)
Pressing the button immediately grants extra screen time on top of daily limits.

### 3. Custom Bonus Duration Input
- **Entity ID**: `number.<child_name>_<device_name>_grant_bonus`
- Enter any number of minutes (e.g., 45) to grant a custom bonus.

---

## 🎨 Dashboard Card Examples (Lovelace)

### Example 1: Entities Card (Simple)
Add an **Entities** card to your dashboard:

```yaml
type: entities
title: "👧 Sofia Screen Time"
entities:
  - entity: sensor.sofia_screen_time_today
    name: "Total Screen Time Today"
  - entity: sensor.sofia_tablet_time_today
    name: "Tablet Time"
  - entity: switch.sofia_tablet_lock
    name: "Lock Tablet"
  - entity: button.sofia_tablet_15m
    name: "Add +15 min"
  - entity: button.sofia_tablet_30m
    name: "Add +30 min"
```

### Example 2: Markdown Card (Display Top Apps)
Add a **Markdown** card to show the breakdown of top used apps:

```yaml
type: markdown
title: "🎮 Top Used Apps Today"
content: >
  **Total:** {{ state_attr('sensor.sofia_screen_time_today', 'formatted_time') }}

  {% for app in state_attr('sensor.sofia_screen_time_today', 'top_apps') %}
    - **{{ app.title }}**: {{ app.minutes }} min
  {% endfor %}
```

### Example 3: Automatic Notification on Expired Cookies/Token
Create an automation to notify your smartphone if authentication requires attention:

```yaml
alias: "Family Link Auth Alert"
trigger:
  - platform: state
    entity_id: binary_sensor.family_link_auth_problem
    to: "on"
action:
  - service: notify.persistent_notification
    data:
      title: "Family Link Needs Attention"
      message: "Family Link credentials have expired. Please update token in add-on."
```

---

## ⚙️ Add-on Configuration Reference

| Option | Type | Default | Description |
|---|---|---|---|
| `mqtt_host` | string | `core-mosquitto` | Hostname of Mosquitto broker |
| `mqtt_port` | port | `1883` | Port of Mosquitto broker |
| `mqtt_user` | string | `""` | MQTT username |
| `mqtt_password` | password | `""` | MQTT password |
| `poll_interval` | int | `300` | Sync interval in seconds (300s = 5 min) |
| `google_email` | string | `""` | Parent Google email |
| `master_token` | password | `""` | Permanent Master Token (`aas_et/...`) |
| `android_id` | string | `""` | 16-hex Android client ID |
| `cookies_text` | string | `""` | Fallback browser cookies (if not using Master Token) |
