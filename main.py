import asyncio
import datetime
import json
import logging

import configuration
import configuration as config
import credentials
import endpoints
import mqtt_integration as mqtt
from request_client import RequestClient


# print functions showing token and current generation in Watts
def get_power_data(client):
    path = endpoints.get_flow_chart_endpoint(credentials.my_plant_id, datetime.date.today())
    r = client.get(path)
    data_response = r.json()
    power_data = data_response['data']

    logging.info(
        f"Got data: SOC: {power_data['soc']}%, Load: {power_data['loadOrEpsPower']}W, PV: {power_data['pvPower']}W, Grid: {power_data['gridOrMeterPower']}W, Charge/Discharge: {power_data['battPower']}W")
    return power_data


def get_energy_data(client):
    path = endpoints.get_month_readings_endpoint(credentials.my_plant_id, datetime.date.today())
    r = client.get(path)
    data_response = r.json()

    energy_data = data_response['data']['infos']

    # PV
    pv_kwh_readings = find_data_stream_for_label("PV", energy_data)
    latest_pv_kwh_reading = get_latest_kwh_reading(pv_kwh_readings)

    # Export
    export_kwh_readings = find_data_stream_for_label("Export", energy_data)
    latest_export_kwh_reading = get_latest_kwh_reading(export_kwh_readings)

    # Import
    import_kwh_readings = find_data_stream_for_label("Import", energy_data)
    latest_import_kwh_reading = get_latest_kwh_reading(import_kwh_readings)

    # Dis Charge
    # this is not a spelling mistake!
    discharge_kwh_readings = find_data_stream_for_label("Dis Charge", energy_data)
    latest_discharge_kwh_reading = get_latest_kwh_reading(discharge_kwh_readings)

    # Charge
    charge_kwh_readings = find_data_stream_for_label("Charge", energy_data)
    latest_charge_kwh_reading = get_latest_kwh_reading(charge_kwh_readings)

    logging.info(
        f"Got Latest kWh readings: PV: {latest_pv_kwh_reading}kWh, Export: {latest_export_kwh_reading}kWh, Import: {latest_import_kwh_reading}kWh, Discharge: {latest_discharge_kwh_reading}kWh, Charge: {latest_charge_kwh_reading}kWh")
    return {
        "pv": latest_pv_kwh_reading,
        "export": latest_export_kwh_reading,
        "import": latest_import_kwh_reading,
        "discharge": latest_discharge_kwh_reading,
        "charge": latest_charge_kwh_reading
    }


def get_latest_kwh_reading(readings):
    return [reading['value'] for reading in readings['records'] if
            reading['time'] == datetime.date.today().strftime("%Y-%m-%d")][0]


def find_data_stream_for_label(label, energy_data):
    return [data for data in energy_data if data['label'] == label][0]


# function that publishes all the powerData values to home assistant over mqtt


class Device():
    device: str

    """A Home Assistant Device, used to group entities."""

    identifiers: []
    connections: []
    configuration_url: str
    manufacturer: str
    model: str
    name: str
    suggested_area: str
    sw_version: str
    via_device: str

    def __attrs_post_init__(self) -> None:
        """Init the class."""
        assert self.identifiers  # Must at least have 1 identifier

    @property
    def id(self) -> str:
        """The device identifier."""
        return str(self.identifiers[0])

class Entity():
    entity_type: str
    entity_name = ""
    group: str
    topic_base:str # f"homeassistant/{entity_type}/{group}/{entity_name}"
    config_topic:str # topic_base + "/config"

    device: Device

    unique_id:str
    name:str
    state_topic:str # = topic_base + "/state"
    unit_of_measurement:str
    icon:str
    device_class:str
    state:str

class SensorEntity(Entity):
    state_topic = ""

    def __init__(self, name, unit_of_measurement, icon, state_topic):
        pass

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
        'payload_press': 'charge', # default from HA is 'PRESS'
        'command_topic': 'homeassistant/button/sunsynk-scraper/charge-button/commands',
    }

    mqttClient.publish("homeassistant/button/sunsynk-scraper/charge-button/config", json.dumps(charge_button))


    soc_config_message = get_mqtt_config_message("battery", "sunsynk-scraper", "soc", "Battery", "%")
    load_config_message = get_mqtt_config_message("power", "sunsynk-scraper", "load", "Load", "W")
    pvPower_config_message = get_mqtt_config_message("power", "sunsynk-scraper", "pvPower", "PV Power", "W")
    gridPower_config_message = get_mqtt_config_message("power", "sunsynk-scraper", "gridPower", "Grid Power", "W")
    battPower_config_message = get_mqtt_config_message("power", "sunsynk-scraper", "battPower", "Battery Power", "W")

    battCharging_config_message = get_binary_sensor_mqtt_config_message("power", "sunsynk-scraper", "battCharging", "Battery Charging Status")


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

    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/soc/config", mqttClient, soc_config_message, qos=2 , retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/load/config", mqttClient, load_config_message, qos=2 , retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/pvPower/config", mqttClient, pvPower_config_message, qos=2 , retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/gridPower/config", mqttClient, gridPower_config_message, qos=2 , retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/battPower/config", mqttClient, battPower_config_message, qos=2 , retain=True)
    mqtt.publish(f"homeassistant/binary_sensor/sunsynk-scraper/battCharging/config", mqttClient, battCharging_config_message, qos=2 , retain=True)

    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/pv/config", mqttClient, pv_energy_config_message, qos=2, retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/export/config", mqttClient, export_energy_config_message, qos=2, retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/import/config", mqttClient, import_energy_config_message, qos=2, retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/discharge/config", mqttClient, discharge_energy_config_message, qos=2, retain=True)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/charge/config", mqttClient, charge_energy_config_message, qos=2, retain=True)

def publish_data_to_home_assistant(client, powerData, energyData):
    is_charging = "ON" if powerData['toBat'] else "OFF"
    battPower = powerData['battPower'] if powerData['toBat'] else 0 - powerData['battPower']
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


async def main():
    setup_logging()
    logging.info("Startup")
    delete = False
    request_client = RequestClient()
    mqttClient = await setup_mqtt()
    logging.info("MQTT setup successful")
    if delete:
        delete_sensors(mqttClient)
    else:
        logging.info("Publishing MQTT config messages")
        publish_discovery_messages(mqttClient)
        subscribeToCommandTopics(mqttClient)
        while True:
            power_data = get_power_data(request_client)
            energy_data = get_energy_data(request_client)
            publish_data_to_home_assistant(mqttClient, power_data, energy_data)
            logging.info("Published data to Home Assistant")
            await asyncio.sleep(config.API_REFRESH_TIMEOUT)


if __name__ == "__main__":
    asyncio.run(main())
