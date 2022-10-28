ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    python3

WORKDIR /app

COPY . ./

RUN chmod a+x /app/run.sh

CMD [ "/app/run.sh" ]