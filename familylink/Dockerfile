ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements
RUN apk add --no-cache jq && \
    pip install --no-cache-dir requests paho-mqtt

WORKDIR /app

COPY familylink_ctl.py /app/
COPY familylink_mqtt.py /app/
COPY run.sh /app/

RUN chmod a+x /app/run.sh

CMD [ "/app/run.sh" ]
