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

## 📊 Monitoring Screen Time & Limits

### 1. Daily Total Screen Time Sensor
- **Entity ID**: `sensor.<child_name>_screen_time_today`
- **State**: Total screen time spent today in **minutes** (e.g. `185`).
- **Attributes**:
  - `formatted_time`: Human-readable format (e.g. `3h 5m`).
  - `date`: Current date (`YYYY-MM-DD`).
  - `top_apps`: Array of applications with minutes spent.

### 2. Remaining Screen Time Quota
- **Entity ID**: `sensor.<child_name>_<device_name>_remaining_time`
- **State**: Remaining regular daily quota in **minutes** directly from Google API.
- **Attributes**:
  - `daily_limit_minutes`: Base daily quota (e.g. 120 min).
  - `active_policy`: Currently active policy (`usageLimit`, `downtime`, `none`).
  - `active_bonus_minutes`: Active bonus minutes.

### 3. Active Bonus Remaining
- **Entity ID**: `sensor.<child_name>_<device_name>_bonus_remaining`
- **State**: Active bonus minutes left until expiration.

### 4. Device Locked Status
- **Entity ID**: `binary_sensor.<child_name>_<device_name>_locked`
- **State**: `on` when locked (limit reached or downtime), `off` when unlocked.

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
- Enter any number of minutes to grant bonus time.

---

## 🎨 Dashboard Card Example (Lovelace)

```yaml
type: entities
title: "👧 Экранное время Софии"
entities:
  - entity: sensor.family_link_sofiia_sofiia_screen_time_today
    name: "Всего потрачено сегодня"
    icon: mdi:timer-outline
  - type: custom:fold-entity-row
    head:
      entity: sensor.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_time_today
      name: "Планшет"
      icon: mdi:tablet-android
    entities:
      - entity: sensor.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_remaining_time
        name: "Остаток лимита"
      - entity: sensor.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_bonus_remaining
        name: "Активный бонус"
      - entity: switch.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_lock
        name: "Блокировка экрана"
      - entity: number.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_grant_bonus
        name: "Выдать бонус (мин)"
```
