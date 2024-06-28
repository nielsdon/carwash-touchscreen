"""An SDK to communicate with Pay.nl API"""
from requests.auth import HTTPBasicAuth
import requests
import configparser
import logging
import json
from washingOrder import Order

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
class PayNL():
    transactionStatusUrl = 'https://rest.pay.nl/v2/transactions/%s'
    createTransactionUrl = 'https://rest.pay.nl/v1/transactions'
    cancelTransactionUrl = 'https://rest.pay.nl/v2/transactions/%s/cancel'
    settings = {}
    
    def __init__(self, settings):
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
        return self.startTransaction(order.amount, order.description, order.id, 'WASH')

    def pay_card_upgrade(self, amount=0, card={}):
        return self.startTransaction(amount, 'washcard top-up', 'top-up', 'TOPUP_'+str(amount))

    def startTransaction(self, amount=0, description='', reference='', extra1='', extra2=''):
        transactionId = ''
        url = self.createTransactionUrl
        # TEST MODE
        try:
            if CONFIG.get('General', 'testMode') == 'True':
                logging.debug('Payment test mode is ON')
                amount = 0.01
        except:
            logging.debug('Payment test mode OFF')
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
                url, headers=self.headers, auth=self.credentials, json=data)
            responseData = json.loads(response.text)
            logging.debug(responseData)
            if (responseData["orderId"]):
                transactionId = responseData['orderId']
            elif (responseData["errors"]):
                raise Exception(responseData["errors"]["general"]["message"])
            else:
                raise Exception()
        except requests.exceptions.RequestException as err:
            logging.error('GENERIC EXCEPTION:\n' + str(err))
        except Exception as err:
            logging.error("Payment error " + repr(err))
        finally:
            logging.debug('Creating transaction done: ' + transactionId)
        return transactionId

    def cancel_transaction(self, transactionId):
        logging.debug("Cancelling transaction...")
        try:
            url = self.cancelTransactionUrl % transactionId
            logging.debug("url:%s", url)
            response = requests.patch(
                url, headers=self.headers, auth=self.credentials)
            logging.debug(response.text)
        except requests.exceptions.RequestException as e:
            logging.error('GENERIC EXCEPTION:\n' + str(e))
        finally:
            logging.debug('Cancelling transaction done')
