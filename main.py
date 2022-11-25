import asyncio
import json
import logging

import configuration
import configuration as config
import mqtt_integration as mqtt
from models import RuntimeSensor, PowerSensor, BatterySensor, EnergySensor, BinarySensor
from request_client import DataIngestService


def get_mqtt_config_message(device_class, group_name, entity_name, friendly_name, unit_of_measurement,
                            measurement=True):
    state_class = "measurement" if measurement else "total_increasing"
    template = f"""
    {{
        "unique_id": "sensor.{group_name}-{entity_name}",
        "name": "Sunsynk {friendly_name}",
        "state_topic": "homeassistant/sensor/{group_name}/{entity_name}/state",
        "unit_of_measurement": "{unit_of_measurement}",
        "device_class": "{device_class}",
        "state_class": "{state_class}"
    }}
    """

    if config.DEBUG_LOGGING:
        logging.info("Generated MQTT config message:")
        logging.info(template)

    return template


def get_binary_sensor_mqtt_config_message(device_class, group_name, entity_name, friendly_name):
    state_class = "measurement"
    template = f"""
    {{
        "unique_id": "binary_sensor.{group_name}-{entity_name}",
        "name": "Sunsynk {friendly_name}",
        "state_topic": "homeassistant/binary_sensor/{group_name}/{entity_name}/state",
        "device_class": "{device_class}"
    }}
    """

    if config.DEBUG_LOGGING:
        logging.info("Generated MQTT config message:")
        logging.info(template)

    return template


def publish_discovery_messages(mqttClient):
    charge_button = {
        'unique_id': 'button.sunsynk-charge-button',
        'name': 'Sunsynk Insta-Charge',
        'state_topic': 'homeassistant/button/sunsynk-scraper/charge-button/state',
        'payload_press': 'charge',  # default from HA is 'PRESS'
        'command_topic': 'homeassistant/button/sunsynk-scraper/charge-button/commands',
    }

    mqttClient.publish("homeassistant/button/sunsynk-scraper/charge-button/config", json.dumps(charge_button))

    soc_config_message = get_mqtt_config_message("battery", "sunsynk-scraper", "soc", "Battery", "%")
    load_config_message = get_mqtt_config_message("power", "sunsynk-scraper", "load", "Load", "W")
    pvPower_config_message = get_mqtt_config_message("power", "sunsynk-scraper", "pvPower", "PV Power", "W")
    gridPower_config_message = get_mqtt_config_message("power", "sunsynk-scraper", "gridPower", "Grid Power", "W")
    battPower_config_message = get_mqtt_config_message("power", "sunsynk-scraper", "battPower", "Battery Power", "W")

    battCharging_config_message = get_binary_sensor_mqtt_config_message("power", "sunsynk-scraper", "battCharging",
                                                                        "Battery Charging Status")

    pv_energy_config_message = get_mqtt_config_message("energy", "sunsynk-scraper", "pv", "PV Energy", "kWh",
                                                       measurement=False)
    export_energy_config_message = get_mqtt_config_message("energy", "sunsynk-scraper", "export", "Export Energy",
                                                           "kWh", measurement=False)
    import_energy_config_message = get_mqtt_config_message("energy", "sunsynk-scraper", "import", "Import Energy",
                                                           "kWh", measurement=False)
    discharge_energy_config_message = get_mqtt_config_message("energy", "sunsynk-scraper", "discharge",
                                                              "Discharge Energy", "kWh", measurement=False)
    charge_energy_config_message = get_mqtt_config_message("energy", "sunsynk-scraper", "charge", "Charge Energy",
                                                           "kWh", measurement=False)

    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/soc/config", mqttClient, soc_config_message, qos=2, retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/load/config", mqttClient, load_config_message, qos=2,
                 retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/pvPower/config", mqttClient, pvPower_config_message, qos=2,
                 retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/gridPower/config", mqttClient, gridPower_config_message, qos=2,
                 retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/battPower/config", mqttClient, battPower_config_message, qos=2,
                 retain=True)
    mqtt.publish(f"homeassistant/binary_sensor/sunsynk-scraper/battCharging/config", mqttClient,
                 battCharging_config_message, qos=2, retain=True)

    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/pv/config", mqttClient, pv_energy_config_message, qos=2,
                 retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/export/config", mqttClient, export_energy_config_message, qos=2,
                 retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/import/config", mqttClient, import_energy_config_message, qos=2,
                 retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/discharge/config", mqttClient, discharge_energy_config_message,
                 qos=2, retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/charge/config", mqttClient, charge_energy_config_message, qos=2,
                 retain=True)


def publish_data_to_home_assistant(client, powerData, energyData):
    is_charging = "ON" if powerData['toBat'] else "OFF"
    battPowerRaw = abs(powerData['toBat'])
    battPower = battPowerRaw if battPowerRaw else 0 - battPowerRaw
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/soc/state", client, powerData['soc'])
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/load/state", client, powerData['loadOrEpsPower'])
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/pvPower/state", client, powerData['pvPower'])
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/gridPower/state", client, powerData['gridOrMeterPower'])
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/battPower/state", client, battPower)
    mqtt.publish("homeassistant/binary_sensor/sunsynk-scraper/battCharging/state", client, is_charging)

    mqtt.publish("homeassistant/sensor/sunsynk-scraper/pv/state", client, energyData['pv'])
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/export/state", client, energyData['export'])
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/import/state", client, energyData['import'])
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/discharge/state", client, energyData['discharge'])
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/charge/state", client, energyData['charge'])


def handle_charge_button_press():
    pass


def on_mqtt_command_message_received(client, userdata, message):
    logging.info("[[ MESSAGE RECEIVED ]] ", str(message.payload.decode("utf-8")))
    logging.info("[[ TOPIC ]] ", message.topic)
    # do your logic here for handling the press command
    # you can use the topic to identify which button was pressed
    # and then perform the appropriate action
    button = message.topic.split("/")[-2]
    logging.info("[[ BUTTON ]] ", button)

    if button == "charge-button":
        logging.info("Charge button pressed")
        handle_charge_button_press()


def subscribeToCommandTopics(mqttClient):
    mqttClient.on_message = on_mqtt_command_message_received
    mqttClient.subscribe("homeassistant/+/sunsynk-scraper/+/commands")


def delete_sensors(mqttClient):
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/soc/config", mqttClient, "")
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/load/config", mqttClient, "")
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/pvPower/config", mqttClient, "")
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/gridPower/config", mqttClient, "")
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/battPower/config", mqttClient, "")


async def setup_mqtt():
    mqttClient = await mqtt.connect_client()
    return mqttClient


def setup_logging():
    loglevel = logging.DEBUG if configuration.DEBUG_LOGGING else logging.INFO
    logging.basicConfig(level=loglevel, format='%(asctime)s | %(levelname)s | %(message)s')


def generate_sensors():
    battery_soc_sensor = BatterySensor("Sunsynk Battery", "soc", "soc")

    power_sensors = [
        PowerSensor("Sunsynk Load", "load", "loadOrEpsPower"),
        PowerSensor("Sunsynk PV Power", "pvPower", "pvPower"),
        PowerSensor("Sunsynk Grid Power", "gridPower", "gridOrMeterPower"),
        PowerSensor("Sunsynk Battery Power", "battPower", "battPower",
                    lambda data: abs(data['battPower']) if data['toBat'] else 0 - abs(data['battPower']))
    ]

    energy_sensors = [
        EnergySensor("Sunsynk PV Energy", "pv", "pv"),
        EnergySensor("Sunsynk Export Energy", "export", "export"),
        EnergySensor("Sunsynk Import Energy", "import", "import"),
        EnergySensor("Sunsynk Discharge Energy", "discharge", "discharge"),
        EnergySensor("Sunsynk Charge Energy", "charge", "charge")
    ]

    runtime_sensor = RuntimeSensor("Sunsynk Battery Estimated Runtime", "runtime", "runtime")

    charging_sensor = BinarySensor("Sunsynk Battery Charging Status", "battCharging", "toBat", "power")

    return battery_soc_sensor, power_sensors, energy_sensors, runtime_sensor, charging_sensor


def publish_discovery_messages_v2(mqttClient, sensors):
    for sensor in sensors:
        if isinstance(sensor, list):
            for s in sensor:
                s.publish_discovery_message(mqttClient)
        else:
            sensor.publish_discovery_message(mqttClient)


def publish_state_updates(mqttClient, energy_data, power_data, sensors):
    data = energy_data | power_data
    for sensor in sensors:
        if isinstance(sensor, list):
            for s in sensor:
                s.publish_state(mqttClient, data)
        else:
            sensor.publish_state(mqttClient, data)


async def main():
    try:
        setup_logging()
        logging.info("Startup")
        delete = False
        data_ingest_service = DataIngestService()
        mqttClient = await setup_mqtt()
        logging.info("MQTT setup successful")

        sensors = generate_sensors()

        if delete:
            delete_sensors(mqttClient)
        else:
            logging.info("Publishing MQTT config messages")
            publish_discovery_messages_v2(mqttClient, sensors)
            subscribeToCommandTopics(mqttClient)
            while True:
                try:
                    power_data = data_ingest_service.get_power_data()
                    energy_data = data_ingest_service.get_energy_data()
                except Exception as e:
                    logging.error("Error getting data from Sunsynk API: " + str(e))
                    continue
                publish_state_updates(mqttClient, energy_data, power_data, sensors)
                logging.info("Published data to Home Assistant")
                await asyncio.sleep(config.API_REFRESH_TIMEOUT)
    except Exception as e:
        logging.error("Error occurred: ", e, exc_info=True)
    finally:
        logging.info("Shutting down due to an error")


if __name__ == "__main__":
    asyncio.run(main())
