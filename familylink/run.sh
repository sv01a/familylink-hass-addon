#!/usr/bin/env bashio
set -e

CONFIG_PATH="/data/options.json"

export MQTT_HOST=$(jq -r '.mqtt_host // "core-mosquitto"' $CONFIG_PATH)
export MQTT_PORT=$(jq -r '.mqtt_port // 1883' $CONFIG_PATH)
export MQTT_USER=$(jq -r '.mqtt_user // ""' $CONFIG_PATH)
export MQTT_PASSWORD=$(jq -r '.mqtt_password // ""' $CONFIG_PATH)
export POLL_INTERVAL=$(jq -r '.poll_interval // 300' $CONFIG_PATH)

export GOOGLE_EMAIL=$(jq -r '.google_email // ""' $CONFIG_PATH)
export MASTER_TOKEN=$(jq -r '.master_token // ""' $CONFIG_PATH)
export ANDROID_ID=$(jq -r '.android_id // ""' $CONFIG_PATH)

if [ -n "$MASTER_TOKEN" ] && [ -n "$GOOGLE_EMAIL" ]; then
    echo "[INFO] Using Google Master Token authentication mode (permanent)."
else
    echo "[WARN] No credentials provided yet. Add-on will start in waiting mode."
fi

echo "[INFO] Starting Google Family Link MQTT Bridge..."
exec python3 /app/familylink_mqtt.py
