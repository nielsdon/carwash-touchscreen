from kivy.app import App 
from kivy.lang import Builder
from kivy.clock import (mainthread, Clock)
from kivy.uix.screenmanager import (ScreenManager, Screen, NoTransition)
from kivy.logger import Logger

from functools import partial
from datetime import datetime
from signal import pause

from paynlsdk.api.client import APIAuthentication
from paynlsdk.api.client import APIClient
from paynlsdk.client.paymentmethods import PaymentMethods
from paynlsdk.client.transaction import Transaction
from paynlsdk.exceptions import *
from paynlsdk.objects import OrderData, Address, Company, datetime, TransactionEndUser,\
    TransactionStartStatsData, TransactionData, SalesData

import os
import time
import configparser
import RPi.GPIO as GPIO
import signal
import sys
import logging

os.environ['KIVY_NO_FILELOG'] = '1'  # eliminate file log
#globals
CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
ERROR_INPUT = int(CONFIG.get('GPIO','errorInput'))
PROGRESS_INPUT = int(CONFIG.get('GPIO','progressInput'))
PROGRESS_LED = int(CONFIG.get('GPIO','progressLED'))
ERROR_LED = int(CONFIG.get('GPIO','errorLED'))
HIGH_VEHICLE_INPUT = int(CONFIG.get('GPIO','highVehicle'))
BIT1LED = int(CONFIG.get('GPIO','BIT1LED'))
BIT2LED = int(CONFIG.get('GPIO','BIT2LED'))
BIT4LED = int(CONFIG.get('GPIO','BIT4LED'))
BIT8LED = int(CONFIG.get('GPIO','BIT8LED'))
Logger.setLevel(int(CONFIG.get('General','logLevel')))
logging.basicConfig(encoding='utf-8', level=int(CONFIG.get('General','logLevel')))

#setup payment
paymentTestMode = False
APIClient.print_debug = False
try:
  if CONFIG.get('Payment','testMode'):
    logging.debug('Payment test mode is ON')
    paymentTestMode = True
except:
  logging.info('Payment test mode OFF')

try:
  if CONFIG.get('Payment','debug'):
    logging.info('Payment debugging ON')
    APIClient.print_debug = True
except:
  logging.info('Payment debugging OFF')

APIAuthentication.service_id = CONFIG.get('Payment','serviceId')
APIAuthentication.api_token = CONFIG.get('Payment','apiToken')
APIAuthentication.token_code = CONFIG.get('Payment','tokenCode')

class ProgramSelection(Screen):
  def selectProgram(self,program):
    app=App.get_running_app()
    app.selectProgram(program)

  def on_enter(self):
    print("=== Program selection ===")

class ProgramSelectionHigh(Screen):
  def selectProgram(self,program):
    app=App.get_running_app()
    app.selectProgram(program)

  def on_enter(self):
    print("=== Program selection for high vehicles ===")

class Payment(Screen):
  def on_enter(self):
    print("=== Payment ===")
    app=App.get_running_app()
    #self.sm.current="payment_failed"
    prices = CONFIG.get('General','prices').split(',')

    if paymentTestMode:
      programPrice = 0.01
    else:
      programPrice = float(prices[app.activeProgram]) + app.uptick
    
    print("Af te rekenen: " +str(programPrice))
    orderId = app.getOrderId()
    
    #pay.nl communicatie: start transaction
    result = {}
    try:
      sinfo1 = {
        'amount': int(programPrice*100),
        'ip_address': '192.168.0.1',
        'finish_url': 'https://192.168.0.1',
        'payment_option_id': int(CONFIG.get('Payment','paymentOptionId')),
        'transaction': TransactionData(
          description='Wasprogramma ' +str(app.activeProgram),
          order_number=str(orderId)),
        'stats_data': TransactionStartStatsData(
          extra1='IDX ' +str(orderId),
          extra2='WP '+str(app.activeProgram)),
        'test_mode': str(paymentTestMode)
      }
      #print(sinfo1)
      result = Transaction.start(**sinfo1)
      #print(result)
      #print('Transaction ID: {id}\nPayment reference: {ref}\nPayment URL: {url}'.format(id=result.transaction.transaction_id, ref=result.get_payment_reference(), url=result.get_redirect_url()))
    except SchemaException as se:
      logging.error('SCHEMA ERROR:\n\t' + str(se))
      print('\nSCHEMA ERRORS:\n\t' + str(se.errors))
    except ErrorException as ee:
      print('API ERROR:\n' + str(ee))
    except Exception as e:
      print('GENERIC EXCEPTION:\n' + str(e))

    #pay.nl communicatie: check order status
    orderStatus = 'PENDING'
    wait = 0
    while orderStatus == 'PENDING' and wait < 10:
      try:
        time.sleep(2)
        statusResult = Transaction.status(transaction_id=result.transaction.transaction_id)
        #print(statusResult)
        orderStatus = statusResult.payment_details.state_name
      except SchemaException as se:
        print('SCHEMA ERROR:\n\t' + str(se))
        print('\nSCHEMA ERRORS:\n\t' + str(se.errors))
      except ErrorException as ee:
        print('API ERROR:\n' + str(ee))
      except Exception as e:
        print('GENERIC EXCEPTION:\n' + str(e))
      print('.')
      time.sleep(2)
      wait += 1
    if(orderStatus == 'PAID'):
      print('betaling gelukt!')
      app.startMachine()
    else:
      print('fout bij betaling')
      app.changeScreen('payment_failed')

class InProgress(Screen):
  pass

class PaymentFailed(Screen):
  def on_enter(self):
    print("=== Payment failed ===")
    app=App.get_running_app()
    Clock.schedule_once(partial(app.changeScreen, "program_selection"),5)

class Error(Screen):
  pass

class Carwash(App):  
  def build(self):
    #setup the screens
    Builder.load_file('screens.kv')

    #setup possible uptick based on weekday
    self.setUptick()
    self.activeProgram = 0

    #setup screens
    self.sm = ScreenManager(transition = NoTransition())
    self.sm.add_widget(ProgramSelection(name="program_selection"))
    self.sm.add_widget(ProgramSelectionHigh(name="program_selection_high"))
    self.sm.add_widget(Payment(name="payment"))
    self.sm.add_widget(PaymentFailed(name="payment_failed"))
    self.sm.add_widget(Error(name="error"))
    self.sm.add_widget(InProgress(name="in_progress"))
    #setup leds
    self.setupIO()  
    return self.sm

  def selectProgram(self,program):
    print("Program selected: " +str(program))
    self.activeProgram = program
    self.changeScreen("payment")
    #Clock.schedule_once(partial(self.changeScreen, "payment"), 3)

  def startMachine(self, dt):
    bin = '{0:04b}'.format(self.activeProgram)
    print("Starting machine. Binary: " +str(bin))
    arr = list(bin)
    print(arr)
    if(int(arr[3])==1):
      GPIO.output(BIT1LED,GPIO.HIGH)
    if(int(arr[2])==1):
      GPIO.output(BIT2LED,GPIO.HIGH)
    if(int(arr[1])==1):
      GPIO.output(BIT4LED,GPIO.HIGH)
    if(int(arr[0])==1):
      GPIO.output(BIT8LED,GPIO.HIGH)
    time.sleep(2)
    GPIO.output(BIT1LED,GPIO.LOW)
    GPIO.output(BIT2LED,GPIO.LOW)
    GPIO.output(BIT4LED,GPIO.LOW)
    GPIO.output(BIT8LED,GPIO.LOW)

  def setUptick(self):
    unmanned_days = CONFIG.get('General','unmannedWeekdays')
    uptick = CONFIG.get('General','mannedUptick')
    programs = CONFIG.get('General','prices')
    self.uptick = 0

  def getOrderId(self):
    orderId = 0
    try:
      file = open('orderId.txt', 'r+')
      read = file.read()
      print('orderId: ' +read)
      if read:
        orderId = int(read)
      print('Gevonden order id: ' +str(orderId))
      orderId += 1
      file.seek(0)
      file.write(str(orderId))
      print('Nieuw order id: ' +str(orderId))
    finally:
      #file.truncate()
      file.close()
    return orderId

  def setupIO(self):
    GPIO.setmode(GPIO.BCM)
    #led setup
    GPIO.setup(ERROR_LED, GPIO.OUT)
    GPIO.setup(PROGRESS_LED, GPIO.OUT)
    GPIO.setup(BIT1LED, GPIO.OUT)  
    GPIO.setup(BIT2LED, GPIO.OUT)  
    GPIO.setup(BIT4LED, GPIO.OUT)  
    GPIO.setup(BIT8LED, GPIO.OUT)
    GPIO.output(BIT1LED,GPIO.LOW)
    GPIO.output(BIT2LED,GPIO.LOW)
    GPIO.output(BIT4LED,GPIO.LOW)
    GPIO.output(BIT8LED,GPIO.LOW)

    #input setup
    GPIO.setup(ERROR_INPUT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(PROGRESS_INPUT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(HIGH_VEHICLE_INPUT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    #machine in progress/done
    GPIO.add_event_detect(PROGRESS_INPUT, GPIO.BOTH, callback=self.progressStatusChanged, bouncetime=300)
    #error detected/resolved
    GPIO.add_event_detect(ERROR_INPUT, GPIO.BOTH, callback=self.errorStatusChanged, bouncetime=300)
    #high vehicle status changed
    GPIO.add_event_detect(HIGH_VEHICLE_INPUT, GPIO.BOTH, callback=self.highVehicleStatusChanged, bouncetime=300)

  def changeScreen(self, screenName, *args):
    print("Showing screen " +screenName)
    self.sm.current=screenName
    
  @mainthread
  def progressStatusChanged(self, *args):
    if GPIO.input(PROGRESS_INPUT):
      print("Machine in progress...")
      GPIO.output(PROGRESS_LED,GPIO.HIGH)
      self.changeScreen("in_progress")
    else:
      print("Machine done!")
      GPIO.output(PROGRESS_LED,GPIO.LOW)
      #show program selection screen
      self.changeScreen("program_selection")

  @mainthread
  def errorStatusChanged(self, *args):
    if GPIO.input(ERROR_INPUT):
      print("Error resolved!")
      #switch on error led
      GPIO.output(ERROR_LED,GPIO.LOW)
      #show program selection screen
      self.changeScreen("program_selection")
    else:
      print("Error detected!")
      #switch on error led
      GPIO.output(ERROR_LED,GPIO.HIGH)
      #show error screen
      self.changeScreen("error")

  @mainthread
  def highVehicleStatusChanged(self, *args):
    if GPIO.input(HIGH_VEHICLE_INPUT):
      print("High vehicle detected!")
      #show program selection screen for high vehicles
      self.changeScreen("program_selection_high")
    else:
      print("High vehicle removed")
      #show normal program selection screen
      self.changeScreen("program_selection")
    
def signal_handler(sig, frame):
    GPIO.cleanup()
    sys.exit(0)
    
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    carwash = Carwash()

    carwash.run()
    #Carwash().run()
