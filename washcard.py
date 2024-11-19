import configparser
import logging
import threading
import select
import subprocess
import requests
import evdev
from munch import munchify
from google_analytics import GoogleAnalytics
from auth_client import AuthClient  # Import AuthClient from the auth module

# Configuration setup
CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
API_URL = 'https://api.washterminalpro.nl'
API_PATH = '/dev' if CONFIG.get('General', 'testMode') == 'True' else '/v1'


class Washcard:
    """Class to handle everything related to the wash cards."""
    cardInfoUrl = API_URL + API_PATH + '/card/%s'
    cardBalanceUrl = API_URL + API_PATH + '/card/%s/balance'
    cardTransactionUrl = API_URL + API_PATH + '/transaction/start'

    def __init__(self, settings):
        self.settings = settings
        self.uid = None
        self.credit = 0
        self.balance = 0
        self.id = None
        self.carwash = None
        self.company = None
        logging.basicConfig(encoding='utf-8', level=int(self.settings["general"]["logLevel"]))

        # Initialize AuthClient for handling authorization and token refreshing
        self.auth_client = AuthClient(API_PATH, CONFIG.get('General', 'apiToken'), CONFIG.get('General', 'apiSecret'))

        # Set up Google Analytics and device settings
        self.ga = GoogleAnalytics()
        self.stop_event = threading.Event()  # Event object for stopping NFC read loop
        self.device = self.find_event_device(self.settings["general"]["nfcReaderVendorIdDeviceId"])
        if not self.device:
            logging.error("NFC Reader not found")

    def find_event_device(self, vendor_product_id):
        """Use bash script to find the connected NFC reader."""
        logging.debug("Finding device %s", vendor_product_id)
        try:
            # Run the shell script with the vendor:product ID as argument
            result = subprocess.run(['./get_hid_device.sh', vendor_product_id],
                                    capture_output=True, text=True, check=True)
            eventDevice = result.stdout.strip()
            logging.debug("NFC Device found: %s", eventDevice)
            return eventDevice
        except subprocess.CalledProcessError as e:
            logging.error("Error finding event device: %s", e.stderr.strip())
            return None

    def load_info(self):
        """Store the retrieved card info in the class."""
        info = self.get_info()
        # Check if the info dictionary has an 'error' key
        if not info or 'error' in info:
            logging.error("Card info could not be loaded: %s", info.get("error", "Unknown error"))
            return False
        info = munchify(info)
        logging.debug('=====INFO: =====')
        logging.debug(info)
        self.carwash = munchify({
            'id': info.carwash_id,
            'name': info.carwash_name,
            'address': info.carwash_address,
            'postal_code': info.carwash_postal_code,
            'city': info.carwash_city,
            'phone': info.carwash_phone
        })
        self.company = munchify({
            'id': info.company_id,
            'name': info.company_name,
            'address': info.company_address,
            'postal_code': info.company_postal_code,
            'city': info.company_city,
            'phone': info.company_phone
        })
        self.balance = info.balance
        self.id = info.id
        self.credit = info.credit

    def get_info(self):
        """Retrieve card info from API."""
        logging.debug('cardinfo(): getting info for card %s', self.uid)
        if not self.uid:
            return {"error": "No UID provided"}

        url = self.cardInfoUrl % self.uid
        headers = self.auth_client.get_authorization_header()
        logging.debug('url: %s', url)

        try:
            response = requests.get(url, headers=headers, timeout=10)

            # Check for a 404 status code to indicate the card was not found
            if response.status_code == 404:
                logging.warning('Card not found for UID %s', self.uid)
                return {"error": "Card not found", "status_code": 404}

            # Raise other HTTP errors
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logging.error('Error fetching card info:\n%s', str(e))
            return {"error": "Request failed", "details": str(e)}

    def pay(self, order):
        """Initialize payment for the selected program."""
        logging.debug('Paying order %s', order.description)
        return self.start_transaction(order.amount * -1, order.description, order.transaction_type)

    def upgrade(self, amount):
        """Initialize top-up for the washcard."""
        logging.debug('Upgrading card %s with € %s', self.uid, str(amount))
        return self.start_transaction(amount, 'Card top-up', 'TOPUP_' + str(amount))

    def start_transaction(self, amount=0, description='', transaction_type=''):
        """Start creating the transaction for the selected program or top-up."""
        logging.debug('Starting transaction')

        url = self.cardTransactionUrl
        data = {
            "carwash_id": self.settings["general"]["carwashId"],
            "card_id": self.id,
            "amount": amount,
            "description": description,
            "transaction_type": transaction_type
        }
        headers = self.auth_client.get_authorization_header()
        logging.debug(data)

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error('Error creating transaction:\n%s', str(e))
            return 3  # Indicate a request error

    def stop_reading(self):
        """Stop the NFC reading loop."""
        self.stop_event.set()

    def read_card(self, callback):
        """Use the NFC reader device to read input."""
        logging.debug("Waiting for NFC UID...")
        if not self.device:
            raise ValueError("Device path is not set. Please provide a valid device path.")

        device = evdev.InputDevice(self.device)
        keyMap = {2: '1', 3: '2', 4: '3', 5: '4', 6: '5', 7: '6', 8: '7', 9: '8', 10: '9', 11: '0'}
        nfcUid = ""
        device.grab()

        try:
            while not self.stop_event.is_set():
                r, _, _ = select.select([device], [], [], 1)
                if device in r:
                    for event in device.read():
                        if event.type == evdev.ecodes.EV_KEY and event.value == 1:
                            keyCode = event.code
                            if keyCode in keyMap:
                                nfcUid += keyMap[keyCode]
                            if keyCode == evdev.ecodes.KEY_ENTER:
                                logging.debug('NFC Card found: %s', nfcUid)
                                self.uid = nfcUid
                                # Attempt to load card information
                                if not self.load_info():
                                    logging.error("Failed to process card: Card not found or loading failed.")
                                try:
                                    callback()
                                except Exception as e:
                                    logging.error("Error in callback execution: %s", e)
                                return
        except (IOError, OSError) as e:
            logging.error("I/O error in NFC read loop: %s", e)
        except KeyboardInterrupt:
            logging.info("NFC read loop interrupted by user.")
        except Exception as e:
            logging.error("Unexpected error in NFC read loop: %s", e)
        finally:
            device.ungrab()
            logging.debug("Exiting NFC reader loop.")
