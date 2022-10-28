ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
#RUN \
#  apk add --no-cache \
#    python3
#
#RUN \
#  apk add --no-cache \
#    python3-pip

RUN apt-get update && apt-get install -y \
     python3=3.9.2 \
     python3-pip

WORKDIR /app

COPY . ./

RUN ls

RUN chmod a+x /app/run.sh

CMD [ "/app/run.sh" ]