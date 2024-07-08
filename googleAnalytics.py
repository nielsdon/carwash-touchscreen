import configparser
import json
import time
import hashlib
import logging
import requests

class GoogleAnalytics:
    """The main Google Analytics class"""
    def __init__(self, config_path='config.ini'):
        # Load credentials from the config.ini file
        config = configparser.ConfigParser()
        config.read(config_path)
        if config.get('General', 'testMode') == 'True':
            logging.basicConfig(encoding='utf-8', level=10)
        else:
            logging.basicConfig(encoding='utf-8', level=50)

        self.measurement_id = config['GA4']['measurement_id']
        self.api_secret = config['GA4']['api_secret']
        self.client_id = config['GA4']['client_id']
        self.event_store = {}
        self.session_id = int(time.time())
        self.event_name = ""
        self.event_params = ""
        self.last_event = None  # Variable to store the last sent event

    def start_new_session(self):
        self.session_id = int(time.time())
        self.send_event('session_start', {})

    def send_event(self, event_name, event_params):
        event_hash = self.get_event_hash(event_name, event_params)
        if event_hash == self.last_event:
            return
        else:
            self.last_event = event_hash
        logging.debug("Tracking:%s", event_name)
        url = f'https://www.google-analytics.com/mp/collect?measurement_id={self.measurement_id}&api_secret={self.api_secret}'
        headers = {"Content-Type": "application/json"}
        # Ensure event time is recent
        event_params["engagement_time_msec"] = event_params.get("engagement_time_msec", "100")
        event_params["session_id"] = self.session_id
        payload = {
            "client_id": self.client_id,
            "events": [
                {
                    "name": event_name,
                    "params": event_params
                }
            ]
        }
        logging.debug("GA4 url:%s", url)
        logging.debug("GA4 payload:%s", payload)

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            logging.debug("Event sent successfully!")
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            logging.error(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            logging.error(f"Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            logging.error(f"An error occurred: {req_err}")

    def add_event_to_store(self, event_name, event_params):
        """Store events to keep them from sending directly"""
        if event_name not in self.event_store:
            self.event_store[event_name] = []
        self.event_store[event_name].append(event_params)

    def send_stored_events(self):
        """Send the previously stored events"""
        for event_name, events in self.event_store.items():
            for event_params in events:
                self.send_event(event_name, event_params)

    def get_event_hash(self, event_name, event_params):
        event_string = f"{event_name}:{json.dumps(event_params, sort_keys=True)}"
        return hashlib.md5(event_string.encode()).hexdigest()

if __name__ == '__main__':
    # Example usage
    ga = GoogleAnalytics()
    # Start a new session
    ga.start_new_session()
    # Add an event to the store
    ga.add_event_to_store('purchase', {'value': 100, 'currency': 'USD'})

    # Send stored events to GA4
    ga.send_stored_events()