import asyncio
import random
import time

from paho.mqtt import client as mqtt_client

import configuration
import credentials

client_id = f'sunsynk-scraper-mqtt-{random.randint(0, 1000)}'


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print("Failed to connect, return code %d\n", rc)
        raise Exception("Failed to connect to MQTT broker")


def on_publish_callback(client, userdata, mid):
    if configuration.DEBUG_LOGGING:
        print(f"Published: {mid}")


async def connect_client():
    username = credentials.mqtt_username
    host = credentials.mqtt_broker
    port = credentials.mqtt_port

    print('MQTT: Connecting to:', username, host, port, credentials.mqtt_password)

    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, credentials.mqtt_password)
    client.on_connect = on_connect
    client.on_publish = on_publish_callback
    client.connect_async(host, port)
    client.loop_start()

    retry = 10
    while retry and not client.is_connected():
        print(f'MQTT: Waiting for connection... ({retry})')
        await asyncio.sleep(1)
        retry -= 1

    if not retry:
        raise ConnectionError(f"MQTT: Could not connect to {username}@{host}:{port}")

    return client


def publish(topic, client, msg, qos = 0, retain = False):
    result = client.publish(topic, msg, qos=qos, retain=retain)
    status = result[0]
    if configuration.DEBUG_LOGGING:
        if status == 0 and configuration.DEBUG_LOGGING:
            print(f"Sent message `{msg}` to topic `{topic}`")
        else:
            print(f"Failed to send message `{msg}` to topic {topic}")
