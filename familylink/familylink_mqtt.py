#!/usr/bin/env python3
"""
Google Family Link <-> Home Assistant MQTT Bridge (MQTT Discovery)
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
import paho.mqtt.client as mqtt
from familylink_ctl import FamilyLinkClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("familylink_mqtt")

MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 300))
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.json")
CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE", "credentials.json")

DISCOVERY_PREFIX = "homeassistant"
BASE_TOPIC = "familylink"

running = True


def handle_signal(sig, frame):
    global running
    logger.info("Termination signal received...")
    running = False


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


class FamilyLinkMQTTBridge:
    def __init__(self):
        self.client_fl = FamilyLinkClient(cookies_file=COOKIES_FILE, credentials_file=CREDENTIALS_FILE)
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="familylink_bridge")
        except AttributeError:
            self.mqtt_client = mqtt.Client(client_id="familylink_bridge")

        if MQTT_USER:
            self.mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message

        self.children = []
        self.device_map = {}
        self.lock_states = {}
        self.bonus_states = {}
        self.auth_ok = True
        self.discovery_published = False

    def init_family(self):
        """Load family members and devices without crashing on auth error"""
        try:
            self.children = self.client_fl.get_family_members()
            logger.info(f"Loaded children count: {len(self.children)}")
            for ch in self.children:
                devs = self.client_fl.get_devices(ch["id"])
                ch["devices"] = devs
                for d in devs:
                    safe_name = d["name"].lower().replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
                    self.device_map[d["id"]] = {
                        "name": d["name"],
                        "child_id": ch["id"],
                        "child_name": ch["name"],
                        "safe_name": safe_name,
                    }
                    self.lock_states[d["id"]] = False
                    self.bonus_states[d["id"]] = 30
                    logger.info(f"  Device: {d['name']} ({d['id']})")
            self.auth_ok = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize family members (auth check failed): {e}")
            self.auth_ok = False
            return False

    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        rc_code = rc.value if hasattr(rc, "value") else rc
        if rc_code == 0:
            logger.info("Connected to MQTT broker successfully!")
            sub_topic = f"{BASE_TOPIC}/+/+/set"
            self.mqtt_client.subscribe(sub_topic)
            logger.info(f"Subscribed to command topic: {sub_topic}")

            self.publish_status_discovery()

            if self.children and not self.discovery_published:
                self.publish_discovery()
                self.discovery_published = True

            self.update_auth_status()
        else:
            logger.error(f"Failed to connect to MQTT broker, return code: {rc_code}")

    def on_mqtt_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8").strip()
            logger.info(f"MQTT command received: {topic} -> {payload}")

            parts = topic.split("/")
            if len(parts) >= 4:
                dev_id = parts[1]
                cmd_type = parts[2]

                dev_info = self.device_map.get(dev_id)
                if not dev_info:
                    logger.warning(f"Unknown device: {dev_id}")
                    return

                child_id = dev_info["child_id"]

                if cmd_type == "lock":
                    if payload.upper() == "ON":
                        ok = self.client_fl.control_device(child_id, dev_id, action="lock")
                        if ok:
                            self.lock_states[dev_id] = True
                            self.mqtt_client.publish(f"{BASE_TOPIC}/{dev_id}/lock/state", "ON", retain=True)
                            self.mqtt_client.publish(f"{BASE_TOPIC}/{dev_id}/is_locked/state", "ON", retain=True)
                    elif payload.upper() == "OFF":
                        ok = self.client_fl.control_device(child_id, dev_id, action="unlock")
                        if ok:
                            self.lock_states[dev_id] = False
                            self.mqtt_client.publish(f"{BASE_TOPIC}/{dev_id}/lock/state", "OFF", retain=True)
                            self.mqtt_client.publish(f"{BASE_TOPIC}/{dev_id}/is_locked/state", "OFF", retain=True)

                elif cmd_type == "grant_bonus":
                    mins = int(float(payload))
                    if mins > 0:
                        ok = self.client_fl.grant_bonus_time(child_id, dev_id, mins)
                        if ok:
                            self.bonus_states[dev_id] = mins
                            self.mqtt_client.publish(f"{BASE_TOPIC}/{dev_id}/bonus/state", str(mins), retain=True)
                            # Instantly reflect active bonus
                            self.mqtt_client.publish(f"{BASE_TOPIC}/{dev_id}/bonus_remaining/state", str(mins), retain=True)
                            self.mqtt_client.publish(f"{BASE_TOPIC}/{dev_id}/is_locked/state", "OFF", retain=True)

        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")
            if "401" in str(e) or "UNAUTHENTICATED" in str(e):
                self.auth_ok = False
                self.update_auth_status()

    def publish_status_discovery(self):
        """Discovery for the bridge status / persistent notification in HA"""
        bridge_device = {
            "identifiers": ["familylink_bridge_service"],
            "name": "Google Family Link Bridge",
            "manufacturer": "Google Family Link",
            "model": "Add-on Bridge",
            "sw_version": "1.3.0",
        }

        problem_config = {
            "name": "Family Link Auth Problem",
            "unique_id": "familylink_auth_problem",
            "state_topic": f"{BASE_TOPIC}/status/auth_problem",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device_class": "problem",
            "device": bridge_device,
        }
        self.mqtt_client.publish(
            f"{DISCOVERY_PREFIX}/binary_sensor/familylink/auth_problem/config",
            json.dumps(problem_config),
            retain=True,
        )

        status_sensor_config = {
            "name": "Family Link Status",
            "unique_id": "familylink_status_message",
            "state_topic": f"{BASE_TOPIC}/status/message",
            "icon": "mdi:shield-account",
            "device": bridge_device,
        }
        self.mqtt_client.publish(
            f"{DISCOVERY_PREFIX}/sensor/familylink/status_message/config",
            json.dumps(status_sensor_config),
            retain=True,
        )

    def update_auth_status(self):
        if self.auth_ok:
            self.mqtt_client.publish(f"{BASE_TOPIC}/status/auth_problem", "OFF", retain=True)
            mode = "Master Token" if self.client_fl.master_token_info else "Cookies"
            self.mqtt_client.publish(f"{BASE_TOPIC}/status/message", f"OK: {mode} Authenticated", retain=True)
        else:
            self.mqtt_client.publish(f"{BASE_TOPIC}/status/auth_problem", "ON", retain=True)
            self.mqtt_client.publish(f"{BASE_TOPIC}/status/message", "ERROR: Authentication Failed", retain=True)

    def publish_discovery(self):
        """Register entities via Home Assistant MQTT Discovery"""
        logger.info("Publishing MQTT Discovery configs to Home Assistant...")

        for ch in self.children:
            child_device = {
                "identifiers": [f"familylink_child_{ch['id']}"],
                "name": f"Family Link ({ch['name']})",
                "manufacturer": "Google",
                "model": "Supervised Child",
            }

            # 1. Total daily screen time
            usage_config = {
                "name": f"{ch['name']} Screen Time Today",
                "unique_id": f"familylink_{ch['id']}_screen_time_today",
                "state_topic": f"{BASE_TOPIC}/{ch['id']}/usage/state",
                "json_attributes_topic": f"{BASE_TOPIC}/{ch['id']}/usage/attributes",
                "unit_of_measurement": "min",
                "icon": "mdi:clock-outline",
                "device": child_device,
            }
            self.mqtt_client.publish(
                f"{DISCOVERY_PREFIX}/sensor/familylink_{ch['id']}/screen_time/config",
                json.dumps(usage_config),
                retain=True,
            )

            # 2. Per-device entities
            for dev in ch.get("devices", []):
                dev_id = dev["id"]
                dev_name = dev["name"]

                hw_device = {
                    "identifiers": [f"familylink_dev_{dev_id}"],
                    "name": f"{ch['name']} {dev_name}",
                    "manufacturer": "Google Family Link",
                    "model": dev_name,
                    "via_device": f"familylink_child_{ch['id']}",
                }

                # Device screen time used sensor
                dev_sensor_config = {
                    "name": f"{ch['name']} {dev_name} Time Today",
                    "unique_id": f"familylink_sensor_{dev_id}_time",
                    "state_topic": f"{BASE_TOPIC}/{dev_id}/time/state",
                    "unit_of_measurement": "min",
                    "icon": "mdi:tablet-cellphone",
                    "device": hw_device,
                }
                self.mqtt_client.publish(
                    f"{DISCOVERY_PREFIX}/sensor/familylink_{dev_id}/time/config",
                    json.dumps(dev_sensor_config),
                    retain=True,
                )

                # Remaining screen time quota sensor
                rem_sensor_config = {
                    "name": f"{ch['name']} {dev_name} Remaining Time",
                    "unique_id": f"familylink_sensor_{dev_id}_remaining_time",
                    "state_topic": f"{BASE_TOPIC}/{dev_id}/remaining_time/state",
                    "json_attributes_topic": f"{BASE_TOPIC}/{dev_id}/remaining_time/attributes",
                    "unit_of_measurement": "min",
                    "icon": "mdi:timer-sand",
                    "device": hw_device,
                }
                self.mqtt_client.publish(
                    f"{DISCOVERY_PREFIX}/sensor/familylink_{dev_id}/remaining_time/config",
                    json.dumps(rem_sensor_config),
                    retain=True,
                )

                # Active bonus remaining sensor
                bonus_rem_config = {
                    "name": f"{ch['name']} {dev_name} Active Bonus",
                    "unique_id": f"familylink_sensor_{dev_id}_bonus_remaining",
                    "state_topic": f"{BASE_TOPIC}/{dev_id}/bonus_remaining/state",
                    "unit_of_measurement": "min",
                    "icon": "mdi:gift-outline",
                    "device": hw_device,
                }
                self.mqtt_client.publish(
                    f"{DISCOVERY_PREFIX}/sensor/familylink_{dev_id}/bonus_remaining/config",
                    json.dumps(bonus_rem_config),
                    retain=True,
                )

                # Device locked status (binary_sensor)
                lock_sensor_config = {
                    "name": f"{ch['name']} {dev_name} Screen Locked",
                    "unique_id": f"familylink_binary_{dev_id}_locked",
                    "state_topic": f"{BASE_TOPIC}/{dev_id}/is_locked/state",
                    "payload_on": "ON",
                    "payload_off": "OFF",
                    "device_class": "lock",
                    "device": hw_device,
                }
                self.mqtt_client.publish(
                    f"{DISCOVERY_PREFIX}/binary_sensor/familylink_{dev_id}/locked/config",
                    json.dumps(lock_sensor_config),
                    retain=True,
                )

                # Lock switch
                lock_config = {
                    "name": f"{ch['name']} {dev_name} Lock",
                    "unique_id": f"familylink_switch_{dev_id}_lock",
                    "command_topic": f"{BASE_TOPIC}/{dev_id}/lock/set",
                    "state_topic": f"{BASE_TOPIC}/{dev_id}/lock/state",
                    "icon": "mdi:cellphone-lock",
                    "device": hw_device,
                }
                self.mqtt_client.publish(
                    f"{DISCOVERY_PREFIX}/switch/familylink_{dev_id}/lock/config",
                    json.dumps(lock_config),
                    retain=True,
                )

                # Single bonus time entity (Number with 30 min default)
                bonus_config = {
                    "name": f"{ch['name']} {dev_name} Add Time",
                    "unique_id": f"familylink_num_{dev_id}_bonus",
                    "command_topic": f"{BASE_TOPIC}/{dev_id}/grant_bonus/set",
                    "state_topic": f"{BASE_TOPIC}/{dev_id}/bonus/state",
                    "min": 5,
                    "max": 240,
                    "step": 5,
                    "unit_of_measurement": "min",
                    "mode": "box",
                    "icon": "mdi:timer-plus-outline",
                    "device": hw_device,
                }
                self.mqtt_client.publish(
                    f"{DISCOVERY_PREFIX}/number/familylink_{dev_id}/grant_bonus/config",
                    json.dumps(bonus_config),
                    retain=True,
                )
                self.mqtt_client.publish(f"{BASE_TOPIC}/{dev_id}/bonus/state", "30", retain=True)

                # Clean up legacy fixed button entities
                for b_suffix in ("bonus_15", "bonus_30", "bonus_60", "plus_15", "plus_30", "plus_60"):
                    self.mqtt_client.publish(f"{DISCOVERY_PREFIX}/button/familylink_{dev_id}/{b_suffix}/config", "", retain=True)

        logger.info("MQTT Discovery configs published successfully.")

    def poll_and_publish_stats(self):
        """Poll Google Family Link API and update MQTT states"""
        self.client_fl.load_auth()

        if not self.children:
            ok = self.init_family()
            if ok and not self.discovery_published:
                self.publish_discovery()
                self.discovery_published = True

        if not self.children:
            self.auth_ok = False
            self.update_auth_status()
            return

        try:
            for ch in self.children:
                child_id = ch["id"]

                # 1. Screen time usage
                usage = self.client_fl.get_screen_time(child_id)
                total_minutes = usage["total_seconds"] // 60
                hours = total_minutes // 60
                mins = total_minutes % 60
                time_str = f"{hours}h {mins}m" if hours else f"{mins}m"

                self.mqtt_client.publish(
                    f"{BASE_TOPIC}/{child_id}/usage/state",
                    str(total_minutes),
                    retain=True,
                )

                apps_summary = [
                    {"title": a["title"], "minutes": a["seconds"] // 60}
                    for a in usage.get("by_app", [])[:15]
                ]
                attributes = {
                    "date": usage.get("date"),
                    "formatted_time": time_str,
                    "top_apps": apps_summary,
                }
                self.mqtt_client.publish(
                    f"{BASE_TOPIC}/{child_id}/usage/attributes",
                    json.dumps(attributes, ensure_ascii=False),
                    retain=True,
                )

                device_sec_map = {d["device_id"]: d["seconds"] for d in usage.get("by_device", [])}
                for dev in ch.get("devices", []):
                    dev_id = dev["id"]
                    sec = device_sec_map.get(dev_id, 0)
                    dev_minutes = sec // 60
                    self.mqtt_client.publish(
                        f"{BASE_TOPIC}/{dev_id}/time/state",
                        str(dev_minutes),
                        retain=True,
                    )

                # 2. Live time limits, lock state, and active bonuses
                limits_map = self.client_fl.get_applied_time_limits(child_id)
                bonus_map = self.client_fl.get_active_bonus_time(child_id)

                for dev in ch.get("devices", []):
                    dev_id = dev["id"]
                    lim = limits_map.get(dev_id, {})
                    rem_mins = lim.get("remaining_minutes", 0)
                    is_locked = lim.get("is_locked", False)
                    active_bonus = bonus_map.get(dev_id, 0)

                    # Update remaining time sensor
                    self.mqtt_client.publish(
                        f"{BASE_TOPIC}/{dev_id}/remaining_time/state",
                        str(rem_mins),
                        retain=True,
                    )
                    rem_attrs = {
                        "daily_limit_minutes": lim.get("daily_limit_minutes", 0),
                        "active_policy": lim.get("active_policy", "none"),
                        "active_bonus_minutes": active_bonus,
                    }
                    self.mqtt_client.publish(
                        f"{BASE_TOPIC}/{dev_id}/remaining_time/attributes",
                        json.dumps(rem_attrs, ensure_ascii=False),
                        retain=True,
                    )

                    # Update active bonus sensor
                    self.mqtt_client.publish(
                        f"{BASE_TOPIC}/{dev_id}/bonus_remaining/state",
                        str(active_bonus),
                        retain=True,
                    )

                    # Update screen locked binary sensor and lock switch state
                    lock_payload = "ON" if is_locked else "OFF"
                    self.mqtt_client.publish(
                        f"{BASE_TOPIC}/{dev_id}/is_locked/state",
                        lock_payload,
                        retain=True,
                    )
                    self.mqtt_client.publish(
                        f"{BASE_TOPIC}/{dev_id}/lock/state",
                        lock_payload,
                        retain=True,
                    )

            if not self.auth_ok:
                self.auth_ok = True
                self.update_auth_status()

            logger.info("Screen time and limit statistics successfully updated in MQTT.")
        except Exception as e:
            logger.error(f"Error updating usage statistics: {e}")
            if "401" in str(e) or "UNAUTHENTICATED" in str(e):
                self.auth_ok = False
                self.update_auth_status()

    def run(self):
        self.init_family()
        self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
        self.mqtt_client.loop_start()

        last_poll = 0
        global running
        try:
            while running:
                now = time.time()
                if now - last_poll >= POLL_INTERVAL:
                    self.poll_and_publish_stats()
                    last_poll = now
                time.sleep(1)
        finally:
            logger.info("Stopping MQTT client...")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()


if __name__ == "__main__":
    bridge = FamilyLinkMQTTBridge()
    bridge.run()
