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

### 2. Add Bonus Screen Time (Number Entity)
- **Entity ID**: `number.<child_name>_<device_name>_add_time`
- Default value is **30 minutes**.
- You can change it to any arbitrary duration (15, 30, 45, 60, etc.) and hit enter/press to grant extra screen time.

---

## 🎨 Dashboard Card Examples (Lovelace)

### Interactive Devices List with Pop-up / Sub-card Controls:

```yaml
type: entities
title: "👧 Экранное время Софии"
entities:
  - entity: sensor.family_link_sofiia_sofiia_screen_time_today
    name: "Всего за сегодня"
    icon: mdi:timer-outline
  - type: custom:fold-entity-row
    head:
      entity: sensor.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_time_today
      name: "Планшет"
      icon: mdi:tablet-android
    entities:
      - entity: switch.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_lock
        name: "Блокировка экрана"
      - entity: number.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_grant_bonus
        name: "Добавить время (мин)"
  - type: custom:fold-entity-row
    head:
      entity: sensor.sofiia_flip_5_sm_f731n_sofiia_flip_5_sm_f731n_time_today
      name: "Flip 5"
      icon: mdi:cellphone
    entities:
      - entity: switch.sofiia_flip_5_sm_f731n_sofiia_flip_5_sm_f731n_lock
        name: "Блокировка экрана"
      - entity: number.sofiia_flip_5_sm_f731n_sofiia_flip_5_sm_f731n_grant_bonus
        name: "Добавить время (мин)"
  - type: custom:fold-entity-row
    head:
      entity: sensor.sofiia_mi_8_sofiia_mi_8_time_today
      name: "MI 8"
      icon: mdi:cellphone-basic
    entities:
      - entity: switch.sofiia_mi_8_sofiia_mi_8_lock
        name: "Блокировка экрана"
      - entity: number.sofiia_mi_8_sofiia_mi_8_grant_bonus
        name: "Добавить время (мин)"
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
