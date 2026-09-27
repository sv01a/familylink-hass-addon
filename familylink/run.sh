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

COOKIES_TEXT=$(jq -r '.cookies_text // ""' $CONFIG_PATH)

if [ -n "$MASTER_TOKEN" ] && [ -n "$GOOGLE_EMAIL" ]; then
    echo "[INFO] Using Google Master Token authentication mode (permanent)."
    export CREDENTIALS_FILE="/app/credentials.json"
    jq -n \
      --arg email "$GOOGLE_EMAIL" \
      --arg master_token "$MASTER_TOKEN" \
      --arg android_id "${ANDROID_ID:-0123456789abcdef}" \
      '{"email": $email, "master_token": $master_token, "android_id": $android_id}' > /app/credentials.json
elif [ -f "/config/familylink/credentials.json" ]; then
    export CREDENTIALS_FILE="/config/familylink/credentials.json"
    echo "[INFO] Using credentials from /config/familylink/credentials.json"
elif [ -n "$COOKIES_TEXT" ]; then
    echo "$COOKIES_TEXT" > /app/cookies.json
    export COOKIES_FILE="/app/cookies.json"
    echo "[INFO] Using cookie-based authentication mode."
elif [ -f "/config/familylink/cookies.json" ]; then
    export COOKIES_FILE="/config/familylink/cookies.json"
    echo "[INFO] Using cookies from /config/familylink/cookies.json"
elif [ -f "/app/cookies.json" ]; then
    export COOKIES_FILE="/app/cookies.json"
    echo "[INFO] Using local cookies file."
else
    echo "[WARN] No credentials or cookies provided yet. Add-on will start in waiting mode."
fi

echo "[INFO] Starting Google Family Link MQTT Bridge..."
exec python3 /app/familylink_mqtt.py
