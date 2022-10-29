import asyncio
import datetime
import time

import requests

import configuration as config
import credentials
import endpoints
import mqtt_integration as mqtt


def get_headers_and_token():
    return {
        'Content-type': 'application/json',
        'Accept': 'application/json',
        'Authorization': credentials.bearer_token,
    }


def get_bearer_token():
    headers = {
        'Content-type': 'application/json',
        'Accept': 'application/json'
    }

    payload = {
        "username": credentials.sunsynk_email,
        "password": credentials.sunsynk_password,
        "grant_type": "password",
        "client_id": "csp-web"
    }
    raw_data = requests.post(endpoints.login_endpoint, json=payload, headers=headers).json()
    # Your access token extracted from response
    my_access_token = raw_data["data"]["access_token"]
    return 'Bearer ' + my_access_token


# Get plant id and current generation in Watts
def get_plant_id():
    r = requests.get(endpoints.plant_id_endpoint, headers=get_headers_and_token())
    data_response = r.json()
    plant_id_and_pac = data_response['data']['infos']
    for d in plant_id_and_pac:
        print(d)
        your_plant_id = d['id']
        print('Your plant id is: ' + str(your_plant_id))
        print('****************************************************')
        return your_plant_id


# print functions showing token and current generation in Watts
def get_power_data():
    path = endpoints.get_flow_chart_endpoint(credentials.my_plant_id, datetime.date.today())

    r = requests.get(path, headers=get_headers_and_token())
    data_response = r.json()
    power_data = data_response['data']

    print(
        f"Got data: SOC: {power_data['soc']}%, Load: {power_data['loadOrEpsPower']}W, PV: {power_data['pvPower']}W, Grid: {power_data['gridOrMeterPower']}W, Charge/Discharge: {power_data['battPower']}W")
    return power_data


def get_energy_data():
    path = endpoints.get_month_readings_endpoint(credentials.my_plant_id, datetime.date.today())
    r = requests.get(path, headers=get_headers_and_token())
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

    print(
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

def publish_data_to_home_assistant(client, powerData, energyData):
    mqtt.publish("homeassistant/sunsynk-scraper/soc", client, powerData['soc'])
    mqtt.publish("homeassistant/sunsynk-scraper/load", client, powerData['loadOrEpsPower'])
    mqtt.publish("homeassistant/sunsynk-scraper/pvPower", client, powerData['pvPower'])
    mqtt.publish("homeassistant/sunsynk-scraper/gridPower", client, powerData['gridOrMeterPower'])
    mqtt.publish("homeassistant/sunsynk-scraper/battPower", client, powerData['battPower'])

    mqtt.publish("homeassistant/sunsynk-scraper/pv", client, energyData['pv'])
    mqtt.publish("homeassistant/sunsynk-scraper/export", client, energyData['export'])
    mqtt.publish("homeassistant/sunsynk-scraper/import", client, energyData['import'])
    mqtt.publish("homeassistant/sunsynk-scraper/discharge", client, energyData['discharge'])
    mqtt.publish("homeassistant/sunsynk-scraper/charge", client, energyData['charge'])


def publish_discovery_messages(mqttClient):
    soc_config_message = get_mqtt_config_message("battery", "sunsynk-scraper", "soc", "Battery", "%")
    load_config_message = get_mqtt_config_message("power", "sunsynk-scraper", "load", "Load", "W")
    pvPower_config_message = get_mqtt_config_message("power", "sunsynk-scraper", "pvPower", "PV Power", "W")
    gridPower_config_message = get_mqtt_config_message("power", "sunsynk-scraper", "gridPower", "Grid Power", "W")
    battPower_config_message = get_mqtt_config_message("power", "sunsynk-scraper", "battPower", "Battery Power", "W")

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

    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/soc/config", mqttClient, soc_config_message)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/load/config", mqttClient, load_config_message)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/pvPower/config", mqttClient, pvPower_config_message)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/gridPower/config", mqttClient, gridPower_config_message)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/battPower/config", mqttClient, battPower_config_message)

    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/pv/config", mqttClient, pv_energy_config_message)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/export/config", mqttClient, export_energy_config_message)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/import/config", mqttClient, import_energy_config_message)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/discharge/config", mqttClient, discharge_energy_config_message)
    mqtt.publish(f"homeassistant/sensor/sunsynk-scraper/charge/config", mqttClient, charge_energy_config_message)


def get_mqtt_config_message(device_class, group_name, entity_name, friendly_name, unit_of_measurement,
                            measurement=True):
    state_class = "measurement" if measurement else "total_increasing"
    template = f"""
    {{
        "unique_id": "sensor.{group_name}-{entity_name}",
        "name": "Sunsynk {friendly_name}",
        "state_topic": "homeassistant/{group_name}/{entity_name}",
        "unit_of_measurement": "{unit_of_measurement}",
        "device_class": "{device_class}",
        "state_class": "{state_class}"
    }}
    """

    if config.DEBUG_LOGGING:
        print("Generated MQTT config message:")
        print(template)

    return template


def subscribeToSetTopic(mqttClient):
    def on_message(client, userdata, message):
        print("message received ", str(message.payload.decode("utf-8")))

    mqttClient.on_message = on_message
    mqttClient.subscribe("homeassistant/+/sunsynk-scraper/+/set")


def delete_sensors(mqttClient):
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/soc/config", mqttClient, "")
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/load/config", mqttClient, "")
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/pvPower/config", mqttClient, "")
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/gridPower/config", mqttClient, "")
    mqtt.publish("homeassistant/sensor/sunsynk-scraper/battPower/config", mqttClient, "")


def login_and_setup_plant():
    credentials.bearer_token = get_bearer_token()
    credentials.my_plant_id = get_plant_id()


async def setup_mqtt():
    mqttClient = await mqtt.connect_client()
    return mqttClient


async def main():
    print("Startup")
    delete = False
    login_and_setup_plant()
    print("Plant retrieval successful")
    try:
        mqttClient = await setup_mqtt()
        print("MQTT setup successful")
        if delete:
            delete_sensors(mqttClient)
        else:
            print("Publishing MQTT config messages")
            publish_discovery_messages(mqttClient)
            subscribeToSetTopic(mqttClient)
            while True:
                power_data = get_power_data()
                energy_data = get_energy_data()
                publish_data_to_home_assistant(mqttClient, power_data, energy_data)
                print("Published data to Home Assistant")
                await asyncio.sleep(config.API_REFRESH_TIMEOUT)
    except Exception as e:
        print(f"Failed to connect to MQTT broker with reason {str(e)}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
