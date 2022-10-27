import random

import config
import credentials
from paho.mqtt import client as mqtt_client

client_id = f'sunsynk-scraper-mqtt-{random.randint(0, 1000)}'

def connect_client():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    def on_publish_callback(client, userdata, mid):
        if config.DEBUG_LOGGING:
            print(f"Published: {mid}")

    client = mqtt_client.Client(client_id)
    client.username_pw_set(credentials.mqtt_username, credentials.mqtt_password)
    client.on_connect = on_connect
    client.connect(credentials.mqtt_broker, credentials.mqtt_port)
    client.on_publish = on_publish_callback

    return client


def publish(topic, client, msg):
    result = client.publish(topic, msg, qos=2)
    status = result[0]
    if config.DEBUG_LOGGING:
        if status == 0 and config.DEBUG_LOGGING:
            print(f"Sent message `{msg}` to topic `{topic}`")
        else:
            print(f"Failed to send message `{msg}` to topic {topic}")