"""SDK for washcards
API is located at api.washterminalpro.nl"""
import configparser
import json
import logging
import requests
import evdev
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
        return True

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
            "carwash_id": CONFIG.get('General', 'carwashId'),
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
        
        # Specify the path to the input device
        input_device_path = self.SETTINGS["general"]["nfcReader"]  # Replace 'eventX' with the correct event number
        
        # Create an instance of the InputDevice class
        device = evdev.InputDevice(input_device_path)
        
        # Create a dictionary to map key codes to characters
        key_map = {
            2: '1', 3: '2', 4: '3', 5: '4', 6: '5',
            7: '6', 8: '7', 9: '8', 10: '9', 11: '0'
        }
        
        # Create an empty string to store the NFC UID
        nfc_uid = ""
        
        # Continuously read events from the input device
        for event in device.read_loop():
            # Check if the stop event has been set
            if self.stop_event.is_set():
                logging.debug("Stopping NFC reader loop.")
                break
            
            # Check if the event is a key event
            if event.type == evdev.ecodes.EV_KEY:
                # Check if it's a key press
                if event.value == 1:
                    # Translate the key code to a character
                    key_code = event.code
                    
                    # Check if the key code is in the key map
                    if key_code in key_map:
                        # Append the character to the NFC UID string
                        nfc_uid += key_map[key_code]
                    
                    # Check if Enter key is pressed
                    if key_code == evdev.ecodes.KEY_ENTER:
                        # Print the NFC UID
                        logging.debug('NFC Card found: %s' ,nfc_uid)
                        self.uid = nfc_uid
                        callback()
                        return self.loadInfo()
