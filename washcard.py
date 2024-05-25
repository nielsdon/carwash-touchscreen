from requests.auth import HTTPBasicAuth
import requests
import configparser
import logging
import json
import subprocess
from munch import *

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
logging.basicConfig(encoding='utf-8', level=int(CONFIG.get('General','logLevel')))

class Washcard():
  cardInfoUrl = 'https://waspasenko.nl/api-dev/card/%s'
  cardBalanceUrl = 'https://waspasenko.nl/api-dev/card/%s/balance'
  cardTransactionUrl = 'https://waspasenko.nl/api-dev/transaction/start'
  uid = ''
  balance = 0
  company = ''
  carwash = ''
  
  def __init__(self):
    self.credentials = HTTPBasicAuth(CONFIG.get('Washcard','apiToken'),CONFIG.get('Washcard','apiSecret'))
    self.headers = {
      "accept": "application/json",
      "content-type": "application/json",
    }

  def loadInfo(self):
    info = self.getInfo()
    if( info == {} ):
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
    logging.debug('cardinfo(): getting info for card ' +self.uid)
    if(self.uid == ''):
      return {}
    url = self.cardInfoUrl % self.uid
    logging.debug('url:' +url)
    status = ''
    data = {}
    try:
      response = requests.get(url, headers=self.headers, auth=self.credentials)
      data = json.loads(response.text)
    except requests.exceptions.RequestException as e:
      logging.error('GENERIC EXCEPTION:\n' + str(e))
      return {}
    finally:
      logging.debug('Getting card info done')
    return data

  def pay(self, order):
    logging.debug('Paying order' +order.description)
    if(self.uid == ''):
      logging.debug('no active card')
      return 2 #no active card

    response = self.startTransaction(order.amount*-1, order.description)
    return response

  def upgrade(self, amount):
    logging.debug('Upgrading card ' +self.uid +' with € ' +str(amount))
    response = self.startTransaction(amount,'Card top-up')
    return response
  
  def startTransaction(self,amount=0,description=''):
    logging.debug('Starting transaction')
    
    url = self.cardTransactionUrl
    data = {
      "carwash_id": CONFIG.get('General','carwashId'),
      "nfc_uid": self.uid,
      "amount": amount,
      "description": description
    }
    logging.debug(data)
    try:
      response = requests.post(url, headers=self.headers, auth=self.credentials, json=data)
      data = json.loads(response.text)
      logging.debug(response.status_code)
      if(response.status_code == 500 ):
        return 1        
    except requests.exceptions.RequestException as e:
      logging.error('GENERIC EXCEPTION:\n' + str(e))
      return 3 #request error
    finally:
      logging.debug('Creating transaction done')
    return 0
    
  def readCard(self):
    if( CONFIG.get('General','NfcReader') == 'acr122u'):
      command = "nfc-poll"
      result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
      nfc_uid = ''
      if(result.returncode != 0):
        return False
        logging.error(result.stderr)
      arr = result.stdout.splitlines()
      data = arr[5].split(': ')
      nfc_uid = ':'.join(data[1].strip().split('  '))
      self.uid = nfc_uid.upper()
      logging.debug(nfc_uid)
      return self.loadInfo()
    else:
      return False
