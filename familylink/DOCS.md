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

### 2. Safe Bonus Workflow: Duration + Grant Button
To prevent accidental bonus grants:
1. **`number.<child_name>_<device_name>_bonus_duration`**: Set desired minutes (default is **30 min**). Changing this value **does not** grant time.
2. **`button.<child_name>_<device_name>_grant_bonus`**: Click this button to **confirm and grant** the selected bonus time to the device.
3. **`button.<child_name>_<device_name>_cancel_bonus`**: Instantly cancel active bonus time overrides.

### 3. Daily Screen Time Limit Control
- **`number.<child_name>_<device_name>_daily_limit`**: Set today's daily screen time limit in minutes (0 to 1440 min). Changes take effect immediately on the child's device!
- **`sensor.<child_name>_<device_name>_daily_limit`**: Displays the active daily limit in minutes.

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
      name: "Планшет (потрачено)"
      icon: mdi:tablet-android
    entities:
      - entity: sensor.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_remaining_time
        name: "Остаток лимита"
        icon: mdi:timer-sand
      - entity: sensor.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_bonus_remaining
        name: "Остаток бонуса"
        icon: mdi:gift-outline
      - entity: binary_sensor.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_screen_locked
        name: "Экран заблокирован"
      - entity: switch.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_lock
        name: "Ручная блокировка"
      - entity: number.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_bonus_duration
        name: "Длительность бонуса (мин)"
      - entity: button.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_grant_bonus
        name: "Выдать бонус"
      - entity: button.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_cancel_bonus
        name: "Отменить бонус"
      - entity: number.sofiia_planshet_23043rp34g_sofiia_planshet_23043rp34g_daily_limit
        name: "Дневной лимит (мин)"
```
