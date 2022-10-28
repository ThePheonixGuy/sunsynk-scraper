ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    python3

WORKDIR /data

COPY . ./

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]