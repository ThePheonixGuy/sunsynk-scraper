ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    python3

WORKDIR /data



# Copy data for add-on
COPY run.sh /


COPY ./* /data/
RUN chmod a+x ./run.sh

CMD [ "./main.py" ]