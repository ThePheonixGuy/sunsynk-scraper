ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    python3

RUN \
  apk add --no-cache \
    python3-pip

# Required for the Debian base
#   https://packages.debian.org/bullseye/python3-dev
# RUN apt-get update && apt-get install -y \
#     python3-dev=3.9.2-3 \
#     python3-pip \
#   && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . ./

RUN chmod a+x /app/run.sh

CMD [ "/app/run.sh" ]