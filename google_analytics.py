import json
import time
import hashlib
import logging
import requests


class GoogleAnalytics:
    """The main Google Analytics class"""
    def __init__(self, measurement_id, api_secret, client_id):
        self.measurement_id = measurement_id
        self.api_secret = api_secret
        self.client_id = client_id
        self.event_store = {}
        self.session_id = int(time.time())
        self.event_name = ""
        self.event_params = ""
        self.last_event = None  # Variable to store the last sent event

    def start_new_session(self):
        self.session_id = int(time.time())
        if self.measurement_id:
            self.send_event('session_start', {})

    def log_page_view(self, page_title, page_location, **additional_params):
        """
        Logs a 'page_view' event with required parameters.
        :param page_title: Title of the page
        :param page_location: URL of the page
        :param additional_params: Any additional parameters to log
        """
        event_params = {
            "page_title": page_title,
            "page_location": page_location,
            "engagement_time_msec": "100",
            "session_id": self.session_id,
            **additional_params,
        }
        self.send_event("page_view", event_params)

    def send_event(self, event_name, event_params):
        """Sends an event to Google Analytics."""
        if not self.measurement_id:
            logging.error("Measurement ID is not set.")
            return False

        # Prevent duplicate events
        event_hash = self.get_event_hash(event_name, event_params)
        if event_hash == self.last_event:
            logging.debug("Duplicate event detected. Skipping.")
            return
        else:
            self.last_event = event_hash

        # Set the endpoint
        url = f'https://www.google-analytics.com/mp/collect?measurement_id={self.measurement_id}&api_secret={self.api_secret}'
        headers = {"Content-Type": "application/json"}

        # Construct the payload
        payload = {
            "client_id": self.client_id,
            "events": [
                {
                    "name": event_name,
                    "params": event_params
                }
            ]
        }

        # Send the request
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
            response.raise_for_status()
            logging.debug("Event sent successfully!")
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending event to Google Analytics: {e}")

        return False

    def track_view_item_list(self, item_list_name, items):
        """
        Tracks the 'view_item_list' event.
        :param item_list_name: Name of the item list being viewed.
        :param items: List of items (dictionaries with 'item_id', 'item_name', etc.).
        """
        event_params = {
            "item_list_name": item_list_name,
            "items": items,
            "engagement_time_msec": "100",
            "session_id": self.session_id
        }
        self.send_event("view_item_list", event_params)

    def track_add_to_cart(self, item):
        """
        Tracks the 'add_to_cart' event.
        :param item: A dictionary with item details ('item_id', 'item_name', 'price', etc.).
        """
        event_params = {
            "items": [item],
            "value": item.get("price", 0),
            "currency": "EUR",
            "engagement_time_msec": "100",
            "session_id": self.session_id
        }
        self.send_event("add_to_cart", event_params)

    def track_add_payment_info(self, payment_method):
        """
        Tracks the 'add_payment_info' event.
        :param payment_method: The payment method used (e.g., 'pin', 'cashcard').
        """
        event_params = {
            "payment_type": payment_method,
            "engagement_time_msec": "100",
            "session_id": self.session_id
        }
        self.send_event("add_payment_info", event_params)

    def track_purchase(self, transaction_id, items, total_value):
        """
        Tracks the 'purchase' event.
        :param transaction_id: Unique transaction ID.
        :param items: List of purchased items (dictionaries with 'item_id', 'item_name', etc.).
        :param total_value: Total value of the purchase.
        """
        event_params = {
            "transaction_id": transaction_id,
            "items": items,
            "value": total_value,
            "currency": "EUR",
            "engagement_time_msec": "100",
            "session_id": self.session_id
        }
        self.send_event("purchase", event_params)

    def add_event_to_store(self, event_name, event_params):
        """Store events to keep them from sending directly"""
        if event_name not in self.event_store:
            self.event_store[event_name] = []
        self.event_store[event_name].append(event_params)

    def send_stored_events(self):
        """Send the previously stored events"""
        if not self.measurement_id:
            return True
        for event_name, events in self.event_store.items():
            for event_params in events:
                self.send_event(event_name, event_params)

    def get_event_hash(self, event_name, event_params):
        event_string = f"{event_name}:{json.dumps(event_params, sort_keys=True)}"
        return hashlib.md5(event_string.encode()).hexdigest()
