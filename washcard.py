"""SDK for washcards
API is located at api.washterminalpro.nl"""
import configparser
import json
import logging
import requests
import subprocess
import evdev
import select  # Import the select module
import threading
from munch import munchify
from googleAnalytics import GoogleAnalytics

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
API_URL = 'https://api.washterminalpro.nl'
if CONFIG.get('General','testMode') == 'True':
    API_PATH = '/dev'
else:
    API_PATH = '/v1'

class Washcard():
    cardInfoUrl = API_URL +API_PATH +'/card/%s'
    cardBalanceUrl = API_URL +API_PATH +'/card/%s/balance'
    cardTransactionUrl = API_URL +API_PATH +'/transaction/start'
    SETTINGS = {}
    id = 0
    uid = ''
    balance = 0
    company = ''
    carwash = ''
    credit = 0
    device = ''

    def __init__(self, settings):
        self.SETTINGS = settings
        logging.basicConfig(encoding='utf-8', level=int(self.SETTINGS["general"]["logLevel"]))
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f'Bearer {self.SETTINGS["general"]["jwtToken"]}'
        }
        self.ga = GoogleAnalytics()
        self.stop_event = threading.Event()  # Create an event object
        self.device = self.find_event_device(self.SETTINGS["general"]["nfcReaderVendorIdDeviceId"])
        if not self.device:
            logging.error("NFC Reader not found")

    def find_event_device(self, vendor_product_id):
        logging.debug("Finding device %s", vendor_product_id)
        try:
            # Run the shell script with the vendor:product ID as argument
            result = subprocess.run(['./get_hid_device.sh', vendor_product_id], capture_output=True, text=True, check=True)
            # Capture the output
            event_device = result.stdout.strip()
            logging.debug("NFC Device found: %s", event_device)
            return event_device
        except subprocess.CalledProcessError as e:
            logging.error(f"Error finding event device: {e.stderr.strip()}")
            return None

    def loadInfo(self):
        info = self.getInfo()
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

    def getInfo(self):
        logging.debug('cardinfo(): getting info for card %s', self.uid)
        if self.uid == '':
            return {}
        url = self.cardInfoUrl % self.uid
        logging.debug('url: %s', url)
        data = {}
        try:
            response = requests.get(url, headers=self.headers)
            data = json.loads(response.text)
        except requests.exceptions.RequestException as e:
            logging.error('GENERIC EXCEPTION:\n%s', str(e))
            return {}
        finally:
            logging.debug('Getting card info done')
        return data

    def pay(self, order):
        logging.debug('Paying order %s', order.description)
        response = self.startTransaction(order.amount*-1, order.description, order.transaction_type)
        return response

    def upgrade(self, amount):
        logging.debug('Upgrading card %s with € %s', self.uid, str(amount))
        response = self.startTransaction(amount, 'Card top-up', 'TOPUP_' +str(amount))
        return response

    def startTransaction(self, amount=0, description='', transaction_type=''):
        logging.debug('Starting transaction')

        url = self.cardTransactionUrl
        data = {
            "carwash_id": self.SETTINGS["general"]["carwashId"],
            "card_id": self.id,
            "amount": amount,
            "description": description,
            "transaction_type": transaction_type
        }
        logging.debug(data)
        try:
            response = requests.post(url, headers=self.headers, json=data)
            data = json.loads(response.text)
            return data
        except requests.exceptions.RequestException as e:
            logging.error('GENERIC EXCEPTION:\n%s', str(e))
            return 3  # request error
        finally:
            logging.debug('Creating transaction done')

    def stopReading(self):
        # Set the stop event to interrupt the loop
        self.stop_event.set()

    def readCard(self, callback):            
        logging.debug("Waiting for NFC UID...")
        
        # Create an instance of the InputDevice class
        print(f"Using device: {self.device}")
        device = evdev.InputDevice(self.device)
        
        # Create a dictionary to map key codes to characters
        key_map = {
            2: '1', 3: '2', 4: '3', 5: '4', 6: '5',
            7: '6', 8: '7', 9: '8', 10: '9', 11: '0'
        }
        
        # Create an empty string to store the NFC UID
        nfc_uid = ""
        
        # Set device to non-blocking mode
        device.grab()

        try:
            while not self.stop_event.is_set():
                r, w, x = select.select([device], [], [], 1)  # 1-second timeout
                if device in r:
                    for event in device.read():
                        if event.type == evdev.ecodes.EV_KEY:
                            if event.value == 1:
                                key_code = event.code
                                if key_code in key_map:
                                    nfc_uid += key_map[key_code]
                                if key_code == evdev.ecodes.KEY_ENTER:
                                    logging.debug('NFC Card found: %s', nfc_uid)
                                    self.uid = nfc_uid
                                    self.loadInfo()
                                    callback()
                                    return
        except Exception as e:
            logging.error("Error in NFC read loop: %s", e)
        finally:
            device.ungrab()
            logging.debug("Card UID: %s", self.uid)
            logging.debug("Exiting NFC reader loop.")

            
            