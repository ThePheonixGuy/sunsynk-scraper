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
        response = requests.get(path, headers= headers)

        if response.ok:
            return response

        if not is_retry and response.status_code == 401:
            logging.info("Got HTTP 401 when calling '%s', refreshing token and trying again", path)
            self.login()
            return self.get(path, is_retry=True)

        logging.error("Request failed: " + str(response.status_code) + " with reason: " + response.text)
        raise Exception("Request failed: " + str(response.status_code))

