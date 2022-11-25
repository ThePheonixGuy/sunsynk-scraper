import asyncio
import logging
import configuration
import configuration as config
import mqtt_integration as mqtt
from models import RuntimeSensor, PowerSensor, BatterySensor, EnergySensor, BinarySensor
from request_client import DataIngestService

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
