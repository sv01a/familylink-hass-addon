ARG BUILD_FROM=ghcr.io/home-assistant/alpine-base:3.19
FROM $BUILD_FROM

ENV LANG C.UTF-8

# Установка Python3 и зависимостей
RUN apk add --no-cache python3 py3-pip jq && \
    pip install --no-cache-dir requests paho-mqtt --break-system-packages

WORKDIR /app

COPY familylink_ctl.py /app/
COPY familylink_mqtt.py /app/
COPY run.sh /app/

RUN chmod a+x /app/run.sh

CMD [ "/app/run.sh" ]
