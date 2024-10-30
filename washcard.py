"""SDK for washcards
API is located at api.washterminalpro.nl"""
import configparser
import json
import logging
import threading
import select
import subprocess
import requests
import evdev
from munch import munchify
from googleAnalytics import GoogleAnalytics

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
API_URL = 'https://api.washterminalpro.nl'
if CONFIG.get('General', 'testMode') == 'True':
    API_PATH = '/dev'
else:
    API_PATH = '/v1'


class Washcard():
    """ Class to handle everything related to the wash cards """
    cardInfoUrl = API_URL + API_PATH + '/card/%s'
    cardBalanceUrl = API_URL + API_PATH + '/card/%s/balance'
    cardTransactionUrl = API_URL + API_PATH + '/transaction/start'
    settings = {}
    id = 0
    uid = ''
    balance = 0
    company = ''
    carwash = ''
    credit = 0
    device = ''

    def __init__(self, settings):
        self.settings = settings
        logging.basicConfig(encoding='utf-8', level=int(self.settings["general"]["logLevel"]))
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f'Bearer {self.settings["general"]["jwtToken"]}'
        }
        self.ga = GoogleAnalytics()
        self.stop_event = threading.Event()  # Create an event object
        self.device = self.find_event_device(self.settings["general"]["nfcReaderVendorIdDeviceId"])
        if not self.device:
            logging.error("NFC Reader not found")

    def find_event_device(self, vendor_product_id):
        """ Use bash script to find the connected nfc reader """
        logging.debug("Finding device %s", vendor_product_id)
        try:
            # Run the shell script with the vendor:product ID as argument
            result = subprocess.run(['./get_hid_device.sh', vendor_product_id],
                                    capture_output=True, text=True, check=True)
            # Capture the output
            eventDevice = result.stdout.strip()
            logging.debug("NFC Device found: %s", eventDevice)
            return eventDevice
        except subprocess.CalledProcessError as e:
            logging.error("Error finding event device: %s", e.stderr.strip())
            return None

    def load_info(self):
        """ store the found info from API in the class """
        info = self.get_info()
        if info == {}:
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
        """ retrieve card info from API """
        logging.debug('cardinfo(): getting info for card %s', self.uid)
        if self.uid == '':
            return {}
        url = self.cardInfoUrl % self.uid
        logging.debug('url: %s', url)
        data = {}
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            data = json.loads(response.text)
        except requests.exceptions.RequestException as e:
            logging.error('GENERIC EXCEPTION:\n%s', str(e))
            return {}
        finally:
            logging.debug('Getting card info done')
        return data

    def pay(self, order):
        """ initialize payment of selected program """
        logging.debug('Paying order %s', order.description)
        response = self.start_transaction(order.amount * -1,
                                          order.description,
                                          order.transaction_type)
        return response

    def upgrade(self, amount):
        """ initialize topup """
        logging.debug('Upgrading card %s with € %s', self.uid, str(amount))
        response = self.start_transaction(amount, 'Card top-up', 'TOPUP_' + str(amount))
        return response

    def start_transaction(self, amount=0, description='', transaction_type=''):
        """ start creating the transaction of selected program or topup """
        logging.debug('Starting transaction')

        url = self.cardTransactionUrl
        data = {
            "carwash_id": self.settings["general"]["carwashId"],
            "card_id": self.id,
            "amount": amount,
            "description": description,
            "transaction_type": transaction_type
        }
        logging.debug(data)
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=10)
            data = json.loads(response.text)
            return data
        except requests.exceptions.RequestException as e:
            logging.error('GENERIC EXCEPTION:\n%s', str(e))
            return 3  # request error
        finally:
            logging.debug('Creating transaction done')

    def stop_reading(self):
        """ set variable to kill the thread """
        # Set the stop event to interrupt the loop
        self.stop_event.set()

    def read_card(self, callback):
        """ use device to read input """
        logging.debug("Waiting for NFC UID...")
        if self.device is None:
            raise ValueError("Device path is not set. Please provide a valid device path.")

        # Create an instance of the InputDevice class
        print(f"Using device: {self.device}")
        device = evdev.InputDevice(self.device)

        # Create a dictionary to map key codes to characters
        keyMap = {
            2: '1', 3: '2', 4: '3', 5: '4', 6: '5',
            7: '6', 8: '7', 9: '8', 10: '9', 11: '0'
        }

        # Create an empty string to store the NFC UID
        nfcUid = ""

        # Set device to non-blocking mode
        device.grab()

        try:
            while not self.stop_event.is_set():
                r, _, _ = select.select([device], [], [], 1)  # 1-second timeout
                if device in r:
                    for event in device.read():
                        if event.type == evdev.ecodes.EV_KEY:
                            if event.value == 1:
                                keyCode = event.code
                                if keyCode in keyMap:
                                    nfcUid += keyMap[keyCode]
                                if keyCode == evdev.ecodes.KEY_ENTER:
                                    logging.debug('NFC Card found: %s', nfcUid)
                                    self.uid = nfcUid
                                    self.load_info()
                                    callback()
                                    return
        except (IOError, OSError) as e:
            logging.error("I/O error in NFC read loop: %s", e)
        except KeyboardInterrupt:
            logging.info("NFC read loop interrupted by user.")
        except Exception as e:
            logging.error("Error in NFC read loop: %s", e)
        finally:
            device.ungrab()
            logging.debug("Card UID: %s", self.uid)
            logging.debug("Exiting NFC reader loop.")
