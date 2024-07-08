"""An SDK to communicate with Pay.nl API"""
import configparser
import logging
import json
import requests
from requests.auth import HTTPBasicAuth


CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
class PayNL():
    """Main Pay.nl class"""
    def __init__(self, settings):
        self.transactionStatusUrl = 'https://rest.pay.nl/v2/transactions/%s'
        self.createTransactionUrl = 'https://rest.pay.nl/v2/transactions'
        self.cancelTransactionUrl = ''
        self.settings = settings
        if CONFIG.get('General', 'testMode') == 'True':
            logging.basicConfig(encoding='utf-8', level=10)
        else:
            logging.basicConfig(encoding='utf-8', level=50)
        self.credentials = HTTPBasicAuth(self.settings["tokenCode"], self.settings["apiToken"])
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }

    def get_transaction_status(self, transactionId):
        """Retrieve transaction status from Pay.nl"""
        url = self.transactionStatusUrl % transactionId
        status = ''
        try:
            response = requests.get(
                url, headers=self.headers, auth=self.credentials)
            data = json.loads(response.text)
            status = data['status']['action']
            logging.debug(response.text)
        except requests.exceptions.RequestException as e:
            logging.error('GENERIC EXCEPTION:\n' + str(e))
        finally:
            logging.debug('Getting transaction status done')
        return str(status)

    def payOrder(self, order):
        return self.startTransaction(order.amount, order.description, order.id, order.program, order.transaction_type)

    def pay_card_upgrade(self, amount=0, card={}):
        return self.startTransaction(amount, 'washcard top-up', 'top-up', 'TOPUP_'+str(amount), 'TOPUP')

    def startTransaction(self, amount=0, description='', reference='', extra1='', extra2=''):
        transactionId = ''
        url = self.createTransactionUrl
        # TEST MODE
        try:
            if CONFIG.get('General', 'testMode') == 'True':
                logging.debug('Payment test mode is ON')
                amount = 0.01
        except Exception as err:
            logging.debug('Payment test mode OFF:%s', str(err))
        # END TEST MODE
        data = {
            "serviceId": self.settings["serviceId"],
            "description": description,
            "reference": reference,
            "returnUrl": "https://demo.pay.nl/complete/",
            "exchangeUrl": "https://demo.pay.nl/exchange.php",
            "amount": {
                "value": int(amount*100),
                "currency": "EUR"
            },
            "paymentMethod": {
                "id": self.settings["paymentOptionId"],
                "subId": self.settings["terminalId"]
            },
            "integration": {
                "testMode": False
            },
            "stats": {
                "info": "Carwash",
                "tool": "WashTerminal Pro",
                "extra1": extra1,
                "extra2": extra2
            }
        }
        logging.debug(data)

        try:
            response = requests.post(
                url, headers=self.headers, auth=self.credentials, json=data, timeout=10)
            responseData = json.loads(response.text)
            logging.debug(responseData)
            if (responseData["orderId"]):
                transactionId = responseData['orderId']
                self.cancelTransactionUrl = responseData["cancelUrl"]
                logging.debug("Cancel transaction url:%s", self.cancelTransactionUrl)
            elif (responseData["errors"]):
                raise Exception(responseData["errors"]["general"]["message"])
            else:
                raise Exception()
        except requests.exceptions.RequestException as err:
            logging.error('GENERIC EXCEPTION:\n%s', str(err))
        except Exception as err:
            logging.error("Payment error %s", repr(err))
        finally:
            logging.debug('Creating transaction done: %s', transactionId)
        return transactionId

    def cancel_transaction(self):
        logging.debug("Cancelling transaction...")
        if not self.cancelTransactionUrl:
            logging.error("Cancel Transaction URL not found!")
            return
        try:
            url = self.cancelTransactionUrl
            logging.debug("url:%s", url)
            response = requests.get(
                url, headers=self.headers, auth=self.credentials, timeout=10)
            logging.debug(response.text)
        except requests.exceptions.RequestException as e:
            logging.error('GENERIC EXCEPTION:\n' + str(e))
        finally:
            logging.debug('Cancelling transaction done')
