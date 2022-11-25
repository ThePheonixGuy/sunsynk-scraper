import json
import logging

import configuration
import mqtt_integration as mqtt


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
    device: Device
    entity_name: str

    unique_id: str
    name: str
    state_topic: str  # = topic_base + "/state"
    unit_of_measurement: str
    icon: str
    device_class: str
    state: str
    state_class: str

    group = "sunsynk-scraper"  # TODO replace with device inclusion
    device_type: str

    def __init__(self, friendly_name, entity_name, key, device_class):
        self.name = friendly_name
        self.entity_name = entity_name
        self.key = key
        self.device_class = device_class

    def get_group_topic(self):
        return f"homeassistant/{self.device_type}/{self.group}"

    def is_valid_for_key(self, key):
            return self.key == key

    def get_state(self, data):
        return data[self.key]


class BinarySensor(Entity):
    def __init__(self, friendly_name, entity_name, key, device_class):
        super().__init__(friendly_name, entity_name, key, device_class)
        self.device_type = "binary_sensor"
        self.unique_id = f"binary_sensor.{self.group}-{self.entity_name}"
        self.base_topic = f"{self.get_group_topic()}/{self.entity_name}"
        self.state_topic = f"{self.base_topic}/state"
        self.config_topic = f"{self.base_topic}/config"

    def get_config(self):
        return json.dumps({
            "unique_id": self.unique_id,
            "name": self.name,
            "state_topic": self.state_topic,
            "device_class": self.device_class
        })

    def get_state(self, data):
        return "ON" if data[self.key] else "OFF"

    def publish_discovery_message(self, mqttClient):
        mqtt.publish(self.config_topic, mqttClient, self.get_config(), qos=2, retain=True)

    def publish_state(self, mqttClient, data):
        mqtt.publish(self.state_topic, mqttClient, self.get_state(data), retain=True)


class Sensor(Entity):
    def __init__(self, friendly_name, entity_name, key, unit_of_measurement, device_class):
        super().__init__(friendly_name, entity_name, key, device_class)
        self.device_type = "sensor"
        self.unit_of_measurement = unit_of_measurement
        self.unique_id = f"sensor.{self.group}-{self.entity_name}"
        self.base_topic = f"{self.get_group_topic()}/{self.entity_name}"
        self.state_topic = f"{self.base_topic}/state"
        self.config_topic = f"{self.base_topic}/config"

    def get_config(self):
        return json.dumps({
            "unique_id": self.unique_id,
            "name": self.name,
            "state_topic": self.state_topic,
            "unit_of_measurement": self.unit_of_measurement,
            "device_class": self.device_class
        })

    def publish_discovery_message(self, mqttClient):
        mqtt.publish(self.config_topic, mqttClient, self.get_config(), qos=2, retain=True)

    def publish_state(self, mqttClient, data):
        mqtt.publish(self.state_topic, mqttClient, self.get_state(data), retain=True)


class StatisticsSensor(Sensor):
    def __init__(self, friendly_name, entity_name, key, unit_of_measurement, device_class, state_class):
        super().__init__(friendly_name, entity_name, key, unit_of_measurement, device_class)
        self.state_class = state_class

    def get_config(self):
        return json.dumps({
            "unique_id": self.unique_id,
            "name": self.name,
            "state_topic": self.state_topic,
            "unit_of_measurement": self.unit_of_measurement,
            "device_class": self.device_class,
            "state_class": self.state_class
        })


class PowerSensor(StatisticsSensor):
    def __init__(self, friendly_name, entity_name, key, get_state_override = None):
        super().__init__(friendly_name, entity_name, key, "W", "power", "measurement")
        self.get_state_override = get_state_override

    def get_state(self, data):
        if self.get_state_override:
            return self.get_state_override(data)
        return data[self.key]


class EnergySensor(StatisticsSensor):
    def __init__(self, friendly_name, entity_name, key):
        super().__init__(friendly_name, entity_name, key, "kWh", "energy", "total_increasing")


class BatterySensor(StatisticsSensor):
    def __init__(self, friendly_name, entity_name, key):
        super().__init__(friendly_name, entity_name, key, "%", "battery", "measurement")


class RuntimeSensor(Sensor):
    def __init__(self, friendly_name, entity_name, key):
        super().__init__(friendly_name, entity_name, key, "h", "duration")

    def get_state(self, data):
        house_load = int(data["loadOrEpsPower"])
        batt_load = data['battPower']
        soc = data['soc']
        charging = True if data['toBat'] else False

        if not charging and abs(batt_load) > 75:
            runtime = (soc - 15) / ((abs(batt_load) /100)  * configuration.BATTERY_DISCHARGE_RATE)
        else:
            runtime = (soc - 15) / ((abs(house_load) /100)  * configuration.BATTERY_DISCHARGE_RATE)

        return runtime
