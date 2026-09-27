ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements including gpsoauth
RUN apk add --no-cache jq python3 py3-pip && \
    pip install --no-cache-dir requests paho-mqtt gpsoauth pycryptodomex --break-system-packages

WORKDIR /app

COPY familylink_ctl.py /app/
COPY familylink_mqtt.py /app/
COPY run.sh /app/

RUN chmod a+x /app/run.sh

CMD [ "/app/run.sh" ]
