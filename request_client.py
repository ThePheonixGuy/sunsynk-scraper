import datetime
import json
import logging
import requests
import credentials
import endpoints


class RequestClient():
    def __init__(self):
        self.login()
        self.setup_plant()
        logging.info("RequestClient configured")

    def login(self):
        credentials.bearer_token = self.get_bearer_token()

    def setup_plant(self):
        credentials.my_plant_id = self.get_plant_id()

    def get_bearer_token(self):
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

    def get_headers_and_token(self):
        return {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            'Authorization': credentials.bearer_token,
        }

    # Get plant id
    def get_plant_id(self):
        r = requests.get(endpoints.plants_endpoint, headers=self.get_headers_and_token())
        data_response = r.json()
        plant_id_and_pac = data_response['data']['infos']
        for d in plant_id_and_pac:
            logging.info(d)
            target_plant_id = d['id']
            logging.info('Your plant id is: ' + str(target_plant_id))
            logging.info('****************************************************')
            return target_plant_id

    def get(self, path, is_retry=False):
        headers = self.get_headers_and_token()
        response = requests.get(path, headers=headers)

        if response.ok:
            return response

        if not is_retry and response.status_code == 401:
            logging.info("Got HTTP 401 when calling '%s', refreshing token and trying again", path)
            self.login()
            return self.get(path, is_retry=True)

        logging.error("Request failed: " + str(response.status_code) + " with reason: " + response.text)
        raise Exception("Request failed: " + str(response.status_code))

    def get_monthly_readings(self):
        path = endpoints.get_month_readings_endpoint(credentials.my_plant_id, datetime.date.today())
        response = self.get(path)
        return response.json()

    def get_power_readings(self):
        path = endpoints.get_flow_chart_endpoint(credentials.my_plant_id, datetime.date.today())
        response = self.get(path)
        return response.json()


class DataIngestService():
    def __init__(self):
        self._client = RequestClient()

    def get_power_data(self):
        response = self._client.get_power_readings()
        power_data = response['data']

        logging.debug(f"Got power data: {json.dumps(power_data, indent=2)}")

        return power_data

    def get_energy_data(self):
        data_response = self._client.get_monthly_readings()

        energy_data = data_response['data']['infos']

        results = {
            "pv": self.get_latest_reading_for_label("PV", energy_data),
            "export": self.get_latest_reading_for_label("Export", energy_data),
            "import": self.get_latest_reading_for_label("Import", energy_data),
            "discharge": self.get_latest_reading_for_label("Dis Charge", energy_data),
            "charge": self.get_latest_reading_for_label("Charge", energy_data)
        }

        logging.debug(f"Got energy data: {json.dumps(results, indent=2)}")
        return results

    def get_latest_reading_for_label(self, label, energy_data):
        readings = self.find_data_stream_for_label(label, energy_data)
        latest_reading = self.get_latest_kwh_reading(readings)
        return latest_reading

    def get_latest_kwh_reading(self, readings):
        results = [reading['value'] for reading in readings['records'] if
                   reading['time'] == datetime.date.today().strftime("%Y-%m-%d")]
        if len(results) == 0:
            raise IOError(f"Could not find a latest reading")

        return results[0]

    def find_data_stream_for_label(self, label, energy_data):
        results = [data for data in energy_data if data['label'] == label]
        if len(results) == 0:
            raise IOError(f"Could not find a data stream for label {label}")

        return results[0]
