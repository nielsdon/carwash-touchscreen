from kivy.app import App 
from kivy.lang import Builder
from kivy.clock import (mainthread, Clock)
from kivy.uix.screenmanager import (ScreenManager, Screen, NoTransition)
from functools import partial
from datetime import datetime
from signal import pause
from paynlsdk.api.client import APIAuthentication
from paynlsdk.api.client import APIClient
from paynlsdk.exceptions import *

import os
import time
import configparser
import RPi.GPIO as GPIO
import signal
import sys

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

#setup payment
APIClient.print_debug = bool(CONFIG.GET('Payment','debug'))
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
    programPrice = float(prices[app.activeProgram]) + app.uptick
    print("Af te rekenen: " +str(programPrice))
    print("Payter communicatie.....")
    #als betaling is gelukt, start dan de machine
    #if(payment_success):
    #Clock.unschedule(event)
    Clock.schedule_once(app.startMachine,3)
#    event = Clock.schedule_once(partial(app.changeScreen, "in_progress"),3)

class InProgress(Screen):
  pass

class PaymentFailed(Screen):
  pass

class PaymentSuccess(Screen):
  pass

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
    self.sm.add_widget(PaymentSuccess(name="payment_success"))
    self.sm.add_widget(PaymentFailed(name="payment_failed"))
    self.sm.add_widget(Error(name="error"))
    self.sm.add_widget(InProgress(name="in_progress"))
    #setup leds
    self.setupIO()
    #self.testLeds()

    #test payment
    try:
      result = PaymentMethods.get_list()
      for payment_method in result.values():
        print('{id}: {name} ({visible_name})'.format(id=payment_method.id, name=payment_method.name,
          visible_name=payment_method.visible_name))
    except SchemaException as se:
      print('SCHEMA ERROR:\n\t' + str(se))
      print('\nSCHEMA ERRORS:\n\t' + str(se.errors))
    except ErrorException as ee:
      print('API ERROR:\n' + str(ee))
    except Exception as e:
      print('GENERIC EXCEPTION:\n' + str(e))
    
    return self.sm

  def selectProgram(self,program):
    print("Program selected: " +str(program))
    self.changeScreen("payment")
    self.activeProgram = program
    Clock.schedule_once(partial(self.changeScreen, "payment"), 3)

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
    
  def testLeds(self):
    GPIO.output(BIT1LED,GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(BIT1LED,GPIO.LOW)
    GPIO.output(BIT2LED,GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(BIT2LED,GPIO.LOW)
    GPIO.output(BIT4LED,GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(BIT4LED,GPIO.LOW)
    GPIO.output(BIT8LED,GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(BIT8LED,GPIO.LOW)
    GPIO.output(ERROR_LED,GPIO.HIGH)    
    time.sleep(0.5)
    GPIO.output(ERROR_LED,GPIO.LOW)
    GPIO.output(PROGRESS_LED,GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(PROGRESS_LED,GPIO.LOW)
    
  def changeScreen(self, screenName, *args):
    print("Showing screen " +screenName)
    self.sm.current=screenName
    
def signal_handler(sig, frame):
    GPIO.cleanup()
    sys.exit(0)
    
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    carwash = Carwash()

    carwash.run()
    #Carwash().run()
