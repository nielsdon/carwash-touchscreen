import logging
import threading
import select
import subprocess
import evdev
import os
from munch import munchify
from auth_client import AuthClient  # Import AuthClient from the auth module
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration setup
API_URL = f"https://api.washterminalpro.nl{'/dev' if os.getenv('TEST_MODE') == '1' else '/v1'}"
TOKEN_URL_SUBDOMAIN_SUFFIX = '-dev' if os.getenv('TEST_MODE') == '1' else '/'
TOKEN_URL = 'https://auth' + TOKEN_URL_SUBDOMAIN_SUFFIX + '.washterminalpro.nl/token'


class Washcard:
    """Class to handle everything related to the wash cards."""
    cardInfoUrl = API_URL + '/card/%s'
    cardBalanceUrl = API_URL + '/card/%s/balance'
    cardTransactionUrl = API_URL + '/transaction/start'

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
        API_TOKEN = str(os.getenv('CLIENT_ID'))
        API_SECRET = str(os.getenv('CLIENT_SECRET'))
        self.auth_client = AuthClient(API_TOKEN, API_SECRET, TOKEN_URL)

        self.stop_event = threading.Event()  # Event object for stopping NFC read loop
        self.device = self.find_event_device(self.settings["general"]["nfcReaderVendorIdDeviceId"])
        if not self.device:
            logging.error("NFC Reader not found")

    def find_event_device(self, vendor_product_id):
        """Use bash script to find the connected NFC reader."""
        logging.debug("Finding device %s", vendor_product_id)
        try:
            # Run the shell script with the vendor:product ID as argument
            result = subprocess.run(['bash', '-c', 'source ./get_hid_device.sh ' + vendor_product_id],
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

        # Ensure `info` is valid and contains necessary data
        if not info or not isinstance(info, dict) or 'error' in info:
            logging.error("Card info could not be loaded: %s", info.get("error", "Unknown error") if isinstance(info, dict) else "Invalid data structure")
            return False

        # Convert to Munch (if needed) and log the data
        info = munchify(info)
        logging.debug("Card info processed successfully: %s", info)

        # Ensure critical fields are present
        if not info.carwash_id or not info.company_id:
            logging.error("Critical card data missing: %s", info)
            return False

        # Populate object attributes
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

        return True

    def get_info(self):
        """Retrieve card info from API."""
        logging.debug('cardinfo(): getting info for card %s', self.uid)
        if not self.uid:
            return {"error": "No UID provided"}

        url = self.cardInfoUrl % self.uid
        logging.debug('url: %s', url)

        try:
            status_code, response = self.auth_client.make_authenticated_request(url)
            # Check for a 404 status code to indicate the card was not found
            if status_code == 404:
                logging.warning('Card not found for UID %s', self.uid)
                return {"error": "Card not found", "status_code": 404}
            return response
        except Exception as e:
            print(f"Unexpected Error: {e}")

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
            "card_id": self.id,
            "amount": amount,
            "description": description,
            "transaction_type": transaction_type
        }
        logging.debug(data)

        try:
            status_code, response = self.auth_client.make_authenticated_request(url, "POST", data)
            return {"status_code": status_code, **response}

        except Exception as e:
            logging.error(f"Washcard payment Error: {e}")
            # Handle insufficient funds error specifically
            if status_code == 462:
                logging.error("Transaction failed: Insufficient funds")
                return {"error": "Insufficient funds", "status_code": status_code}
            return {"error": "Unexpected error", "details": str(e)}

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
                                    logging.error("Failed to process card. Card UID: %s", self.uid)
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
