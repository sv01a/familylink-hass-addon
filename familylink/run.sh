#!/usr/bin/env bashio
set -e

CONFIG_PATH="/data/options.json"

export MQTT_HOST=$(jq -r '.mqtt_host // "core-mosquitto"' $CONFIG_PATH)
export MQTT_PORT=$(jq -r '.mqtt_port // 1883' $CONFIG_PATH)
export MQTT_USER=$(jq -r '.mqtt_user // ""' $CONFIG_PATH)
export MQTT_PASSWORD=$(jq -r '.mqtt_password // ""' $CONFIG_PATH)
export POLL_INTERVAL=$(jq -r '.poll_interval // 300' $CONFIG_PATH)

COOKIES_TEXT=$(jq -r '.cookies_text // ""' $CONFIG_PATH)

if [ -n "$COOKIES_TEXT" ]; then
    echo "$COOKIES_TEXT" > /app/cookies.json
    export COOKIES_FILE="/app/cookies.json"
    echo "[INFO] Loaded cookies from add-on configuration."
elif [ -f "/config/familylink/cookies.json" ]; then
    export COOKIES_FILE="/config/familylink/cookies.json"
    echo "[INFO] Using cookies from /config/familylink/cookies.json"
elif [ -f "/app/cookies.json" ]; then
    export COOKIES_FILE="/app/cookies.json"
    echo "[INFO] Using local cookies file."
else
    echo "[ERROR] No cookies found! Please paste your cookies in the add-on configuration or place cookies.json in /config/familylink/cookies.json"
    exit 1
fi

echo "[INFO] Starting Google Family Link MQTT Bridge..."
exec python3 /app/familylink_mqtt.py
