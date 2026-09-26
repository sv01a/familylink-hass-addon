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

# Настройки MQTT (можно переопределить через переменные окружения)
MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 300))  # 5 минут по умолчанию
COOKIES_FILE = os.getenv("COOKIES_FILE", "cookies.json")

DISCOVERY_PREFIX = "homeassistant"
BASE_TOPIC = "familylink"

running = True

def handle_signal(sig, frame):
    global running
    logger.info("Получен сигнал завершения...")
    running = False

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


class FamilyLinkMQTTBridge:
    def __init__(self):
        self.client_fl = FamilyLinkClient(cookies_file=COOKIES_FILE)
        # Поддержка paho-mqtt v1 и v2
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="familylink_bridge")
        except AttributeError:
            self.mqtt_client = mqtt.Client(client_id="familylink_bridge")
        if MQTT_USER:
            self.mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message

        self.children = []
        self.device_map = {}  # device_id -> {name, child_id, safe_name}
        self.lock_states = {}  # device_id -> bool

    def init_family(self):
        """Загрузка детей и их устройств"""
        self.children = self.client_fl.get_family_members()
        logger.info(f"Загружено детей: {len(self.children)}")
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
                logger.info(f"  Устройство: {d['name']} ({d['id']})")

    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        rc_code = rc.value if hasattr(rc, "value") else rc
        if rc_code == 0:
            logger.info("Подключено к MQTT брокеру!")
            # Подписываемся на команды
            sub_topic = f"{BASE_TOPIC}/+/+/set"
            self.mqtt_client.subscribe(sub_topic)
            logger.info(f"Подписка на топик команд: {sub_topic}")
            self.publish_discovery()
        else:
            logger.error(f"Ошибка подключения к MQTT, код: {rc}")

    def on_mqtt_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8").strip()
            logger.info(f"Получена команда MQTT: {topic} -> {payload}")

            # Формат топика: familylink/<device_id>/<command_type>/set
            parts = topic.split("/")
            if len(parts) >= 4:
                dev_id = parts[1]
                cmd_type = parts[2]

                dev_info = self.device_map.get(dev_id)
                if not dev_info:
                    logger.warning(f"Неизвестное устройство: {dev_id}")
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
                    # Кнопки с фиксированным бонусом (bonus_15, bonus_30, bonus_60)
                    mins = int(cmd_type.split("_")[1])
                    self.client_fl.grant_bonus_time(child_id, dev_id, mins)

                elif cmd_type == "grant_bonus":
                    # Ввод произвольных минут
                    mins = int(float(payload))
                    if mins > 0:
                        self.client_fl.grant_bonus_time(child_id, dev_id, mins)

        except Exception as e:
            logger.error(f"Ошибка обработки команды MQTT: {e}", exc_info=True)

    def publish_discovery(self):
        """Регистрация устройств и сенсоров через Home Assistant MQTT Discovery"""
        logger.info("Отправка MQTT Discovery для Home Assistant...")

        for ch in self.children:
            child_safe = ch["name"].lower().replace(" ", "_")
            child_device = {
                "identifiers": [f"familylink_child_{ch['id']}"],
                "name": f"Family Link ({ch['name']})",
                "manufacturer": "Google",
                "model": "Supervised Child",
            }

            # 1. Главный сенсор: общее экранное время за день
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

            # 2. Сущности для каждого устройства
            for dev in ch.get("devices", []):
                dev_id = dev["id"]
                dev_name = dev["name"]
                dev_safe = self.device_map[dev_id]["safe_name"]

                hw_device = {
                    "identifiers": [f"familylink_dev_{dev_id}"],
                    "name": f"{ch['name']} {dev_name}",
                    "manufacturer": "Google Family Link",
                    "model": dev_name,
                    "via_device": f"familylink_child_{ch['id']}",
                }

                # Сенсор времени устройства
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

                # Переключатель блокировки
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

                # Кнопки быстрого бонуса: +15, +30, +60 минут
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

                # Числовой ввод бонуса (Number)
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

        logger.info("MQTT Discovery опубликован.")

    def poll_and_publish_stats(self):
        """Периодический опрос Google API и публикация сенсоров"""
        try:
            for ch in self.children:
                child_id = ch["id"]
                usage = self.client_fl.get_screen_time(child_id)

                total_minutes = usage["total_seconds"] // 60
                hours = total_minutes // 60
                mins = total_minutes % 60
                time_str = f"{hours} ч {mins} мин" if hours else f"{mins} мин"

                # 1. Публикуем общее время
                self.mqtt_client.publish(
                    f"{BASE_TOPIC}/{child_id}/usage/state",
                    str(total_minutes),
                    retain=True,
                )

                # Топ приложений в атрибуты
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

                # 2. Публикуем время по каждому девайсу
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

            logger.info("Статистика экранного времени успешно обновлена в MQTT.")
        except Exception as e:
            logger.error(f"Ошибка при опросе статистики: {e}", exc_info=True)

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
            logger.info("Остановка MQTT клиента...")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()


if __name__ == "__main__":
    bridge = FamilyLinkMQTTBridge()
    bridge.run()
