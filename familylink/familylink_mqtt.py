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
        self.client_fl = FamilyLinkClient(cookies_file=COOKIES_FILE)
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
                    logger.info(f"  Device: {d['name']} ({d['id']})")
            self.auth_ok = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize family members (likely expired cookies): {e}")
            self.auth_ok = False
            return False

    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        rc_code = rc.value if hasattr(rc, "value") else rc
        if rc_code == 0:
            logger.info("Connected to MQTT broker successfully!")
            sub_topic = f"{BASE_TOPIC}/+/+/set"
            self.mqtt_client.subscribe(sub_topic)
            logger.info(f"Subscribed to command topic: {sub_topic}")

            # Publish service status discovery entity
            self.publish_status_discovery()

            # Publish device discovery if family is initialized
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
                    elif payload.upper() == "OFF":
                        ok = self.client_fl.control_device(child_id, dev_id, action="unlock")
                        if ok:
                            self.lock_states[dev_id] = False
                            self.mqtt_client.publish(f"{BASE_TOPIC}/{dev_id}/lock/state", "OFF", retain=True)

                elif cmd_type.startswith("bonus_"):
                    mins = int(cmd_type.split("_")[1])
                    self.client_fl.grant_bonus_time(child_id, dev_id, mins)

                elif cmd_type == "grant_bonus":
                    mins = int(float(payload))
                    if mins > 0:
                        self.client_fl.grant_bonus_time(child_id, dev_id, mins)

        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")
            if "401" in str(e) or "SESSION_COOKIE_INVALID" in str(e):
                self.auth_ok = False
                self.update_auth_status()

    def publish_status_discovery(self):
        """Discovery for the bridge status / persistent notification in HA"""
        bridge_device = {
            "identifiers": ["familylink_bridge_service"],
            "name": "Google Family Link Bridge",
            "manufacturer": "Google Family Link",
            "model": "Add-on Bridge",
            "sw_version": "1.0.0",
        }

        # Binary Sensor: Problem / Cookies Expired
        problem_config = {
            "name": "Family Link Cookies Expired",
            "unique_id": "familylink_cookies_expired",
            "state_topic": f"{BASE_TOPIC}/status/cookies_expired",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device_class": "problem",
            "device": bridge_device,
        }
        self.mqtt_client.publish(
            f"{DISCOVERY_PREFIX}/binary_sensor/familylink/cookies_expired/config",
            json.dumps(problem_config),
            retain=True,
        )

        # Sensor: Status Message
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
        """Update problem binary_sensor and notify Home Assistant via persistent_notification"""
        if self.auth_ok:
            self.mqtt_client.publish(f"{BASE_TOPIC}/status/cookies_expired", "OFF", retain=True)
            self.mqtt_client.publish(f"{BASE_TOPIC}/status/message", "OK: Cookies Valid", retain=True)
        else:
            self.mqtt_client.publish(f"{BASE_TOPIC}/status/cookies_expired", "ON", retain=True)
            self.mqtt_client.publish(f"{BASE_TOPIC}/status/message", "ERROR: Cookies Expired", retain=True)

            # Send persistent notification to Home Assistant via MQTT Discovery service/notification
            notification = {
                "message": "Google Family Link session cookies have expired! Please update `cookies_text` in the add-on configuration tab.",
                "title": "Family Link: Cookies Expired",
                "notification_id": "familylink_cookies_expired",
            }
            # Also publish notification payload for users using MQTT automations
            self.mqtt_client.publish(
                f"{BASE_TOPIC}/notification/cookies_expired",
                json.dumps(notification),
                retain=True,
            )

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

                # Device screen time sensor
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

                # Quick bonus buttons (+15, +30, +60 min)
                for mins in [15, 30, 60]:
                    btn_config = {
                        "name": f"{ch['name']} {dev_name} +{mins}m",
                        "unique_id": f"familylink_btn_{dev_id}_plus_{mins}",
                        "command_topic": f"{BASE_TOPIC}/{dev_id}/bonus_{mins}/set",
                        "payload_press": "PRESS",
                        "icon": "mdi:plus-circle-outline",
                        "device": hw_device,
                    }
                    self.mqtt_client.publish(
                        f"{DISCOVERY_PREFIX}/button/familylink_{dev_id}/bonus_{mins}/config",
                        json.dumps(btn_config),
                        retain=True,
                    )

                # Custom bonus input (Number)
                num_config = {
                    "name": f"{ch['name']} {dev_name} Grant Bonus",
                    "unique_id": f"familylink_num_{dev_id}_bonus",
                    "command_topic": f"{BASE_TOPIC}/{dev_id}/grant_bonus/set",
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
                    json.dumps(num_config),
                    retain=True,
                )

        logger.info("MQTT Discovery configs published successfully.")

    def poll_and_publish_stats(self):
        """Poll Google Family Link API and update MQTT states"""
        # Reload cookies from file in case user updated them
        self.client_fl.load_cookies()

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

            if not self.auth_ok:
                self.auth_ok = True
                self.update_auth_status()

            logger.info("Screen time statistics successfully updated in MQTT.")
        except Exception as e:
            logger.error(f"Error updating usage statistics (cookies may have expired): {e}")
            if "401" in str(e) or "SESSION_COOKIE_INVALID" in str(e):
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
