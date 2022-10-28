ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    python3

RUN pip3 install --no-cache-dir --disable-pip-version-check paho-mqtt~=1.6.1 requests~=2.28.1

WORKDIR /data

COPY . ./

# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "./main.py" ]