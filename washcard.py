"""SDK for washcards
API is located at api.washterminalpro.nl"""
import configparser
import json
import logging
import subprocess
import requests
import evdev
from munch import munchify
from requests.auth import HTTPBasicAuth

API_URL = 'https://api.washterminalpro.nl'
API_PATH = '/v1'

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
logging.basicConfig(
    encoding='utf-8', level=int(CONFIG.get('General', 'logLevel')))


class Washcard():
    cardInfoUrl = API_URL +API_PATH +'/card/%s'
    cardBalanceUrl = API_URL +API_PATH +'/card/%s/balance'
    cardTransactionUrl = API_URL +API_PATH +'/transaction/start'
    uid = ''
    balance = 0
    company = ''
    carwash = ''

    def __init__(self):
        self.credentials = HTTPBasicAuth(CONFIG.get(
            'Washcard', 'apiToken'), CONFIG.get('Washcard', 'apiSecret'))
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }

    def loadInfo(self):
        info = self.getInfo()
        if (info == {}):
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
        return True

    def getInfo(self):
        logging.debug('cardinfo(): getting info for card %s', self.uid)
        if self.uid == '':
            return {}
        url = self.cardInfoUrl % self.uid
        logging.debug('url: %s', url)
        data = {}
        try:
            response = requests.get(url, headers=self.headers, auth=self.credentials)
            data = json.loads(response.text)
        except requests.exceptions.RequestException as e:
            logging.error('GENERIC EXCEPTION:\n%s', str(e))
            return {}
        finally:
            logging.debug('Getting card info done')
        return data

    def pay(self, order):
        logging.debug('Paying order %s', order.description)
        if self.uid == '':
            logging.debug('no active card')
            return 2  # no active card

        response = self.startTransaction(order.amount*-1, order.description)
        return response

    def upgrade(self, amount):
        logging.debug('Upgrading card %s with € %s', self.uid, str(amount))
        response = self.startTransaction(amount, 'Card top-up')
        return response

    def startTransaction(self, amount=0, description=''):
        logging.debug('Starting transaction')

        url = self.cardTransactionUrl
        data = {
            "carwash_id": CONFIG.get('General', 'carwashId'),
            "nfc_uid": self.uid,
            "amount": amount,
            "description": description
        }
        logging.debug(data)
        try:
            response = requests.post(
                url, headers=self.headers, auth=self.credentials, json=data)
            data = json.loads(response.text)
            logging.debug(response.status_code)
            if response.status_code == 500:
                return 1
        except requests.exceptions.RequestException as e:
            logging.error('GENERIC EXCEPTION:\n%s', str(e))
            return 3  # request error
        finally:
            logging.debug('Creating transaction done')
        return 0

    def readCard(self):            
        if CONFIG.get('General', 'nfcReader') == 'acr122u':
            command = "nfc-poll"
            result = subprocess.run(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            nfc_uid = ''
            if result.returncode != 0:
                logging.error(result.stderr)
                return False
            arr = result.stdout.splitlines()
            data = arr[5].split(': ')
            nfc_uid = ':'.join(data[1].strip().split('  '))
            self.uid = nfc_uid.upper()
            logging.debug(nfc_uid)
            return self.loadInfo()
        else:
            logging.debug("Waiting for NFC UID...")
            
            # Specify the path to the input device
            input_device_path = CONFIG.get('General', 'nfcReader')  # Replace 'eventX' with the correct event number
            
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
                            return self.loadInfo()
