ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    python3

WORKDIR /data

COPY . ./data/

RUN chmod a+x /data/run.sh

CMD [ "/data/run.sh" ]