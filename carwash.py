"""Carwash class"""
import sys
import os
import configparser
import locale
import logging
import time
import json
import netifaces
import pigpio
import requests

from kivy.app import App
from kivy.clock import mainthread
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.uix.screenmanager import NoTransition, ScreenManager, ScreenManagerException
from washingOrder import Order
from googleAnalytics import GoogleAnalytics
from statusLight import Status_light

sys.path.append(os.path.join(os.path.dirname(__file__), 'screens'))
from paymentFailed import PaymentFailed
from error import Error
from inProgress import InProgress
from moveVehicle import MoveVehicle
from payment import Payment
from paymentMethod import PaymentMethod
from paymentSuccess import PaymentSuccess
from paymentWashcard import PaymentWashcard
from paymentWashcardCardNotFound import PaymentWashcardCardNotFound
from paymentWashcardCardNotValid import PaymentWashcardCardNotValid
from paymentWashcardInsufficientBalance import PaymentWashcardInsufficientBalance
from paymentWashcardWrongCarwash import PaymentWashcardWrongCarwash
from programSelection import ProgramSelection
from programSelectionHigh import ProgramSelectionHigh
from upgradeWashcardChooseAmount import UpgradeWashcardChooseAmount
from upgradeWashcardPayment import UpgradeWashcardPayment
from upgradeWashcardCredit import UpgradeWashcardCredit
from upgradeWashcardPaymentFailed import UpgradeWashcardPaymentFailed
from upgradeWashcardPaymentSuccess import UpgradeWashcardPaymentSuccess
from upgradeWashcardReadCard import UpgradeWashcardReadCard

os.environ['KIVY_NO_FILELOG'] = '1'  # eliminate file log
# globals
CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
API_TOKEN = str(CONFIG.get('General', 'apiToken'))
API_SECRET = str(CONFIG.get('General', 'apiSecret'))
TEST_MODE = bool(CONFIG.get('General', 'testMode') == 'True')
SETTINGS = {}
pi = pigpio.pi()
if not pi.connected:
    exit()
if TEST_MODE:
    API_PATH = 'dev'
    os.environ['KIVY_NO_CONSOLELOG'] = '0'  # Enable console logging
    os.environ['KIVY_LOG_LEVEL'] = 'debug'  # Set log level to debug
else:
    API_PATH = 'v1'
    os.environ['KIVY_NO_CONSOLELOG'] = '0'  # Enable console logging
    os.environ['KIVY_LOG_LEVEL'] = 'debug'  # Set log level to debug

locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')

class Carwash(App):
    """ class definition """
    activeOrder = ''
    activeWashcard = ''
    washcardTopup = 0
    carwash_id = 0
    jwt_token = ''
    TEST_MODE = True
    SETTINGS = {}
    buttonBackgroundColor = [1,1,1,1]
    buttonTextColor = [0,0,0,1]
    textColor = [0,0,0,1]
    backgroundColor = [1,1,1,1]
    supportPhone = ''
    in_position = 0
    error = 1
    high = 0
    busy = 0
    status_light = None
    carwash_name = ''

    def __init__(self, **kwargs):
        super(Carwash, self).__init__(**kwargs)
        # Init globals
        self.TEST_MODE = TEST_MODE

        # Get the IP address
        self.ip_address = self.get_ip_address()

        # Initialize API connection and settings
        url = f'https://api.washterminalpro.nl/{API_PATH}/login/'
        response = requests.post(url, json={"username": API_TOKEN, "password": API_SECRET}, timeout=10)
        if response.status_code != 200:
            response.raise_for_status()

        responseData = response.json()
        self.carwash_name = responseData["carwash_name"]
        self.carwash_id = responseData["carwash_id"]
        self.jwt_token = responseData["jwt"]
        self.load_settings()

        # Setup window and screen manager
        Window.rotation = 90
        Window.show_cursor = False
        self.setupIO()

        # Setup Google Analytics
        self.ga = GoogleAnalytics()

        self.sm = None

    def get_ip_address(self):
        """retrieve the IP address; will be shown on screen in test mode"""
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            addresses = netifaces.ifaddresses(interface)
            # Check for IPv4 address
            if netifaces.AF_INET in addresses:
                ipv4 = addresses[netifaces.AF_INET][0]['addr']
                if ipv4 != '127.0.0.1':  # Ignore localhost
                    return ipv4

    def build(self):
        """ Create and return the root widget (ScreenManager)"""
        self.sm = ScreenManager(transition=NoTransition())
        self.load_screens()
        # show the test label with IP address in test mode
        if TEST_MODE:
            screen = self.sm.get_screen("program_selection")
            screen.ids.test_label.text = "TEST - " +self.ip_address
            screen = self.sm.get_screen("program_selection_high")
            screen.ids.test_label.text = "TEST - " +self.ip_address
        
        # start operation
        self.show_start_screen()
        return self.sm

    def load_screens(self):
        """ setup screens"""
        self.sm.add_widget(MoveVehicle(name="move_vehicle"))
        self.sm.add_widget(ProgramSelection(name="program_selection", settings=self.SETTINGS))
        self.sm.add_widget(ProgramSelectionHigh(name="program_selection_high", settings=self.SETTINGS))
        self.sm.add_widget(PaymentMethod(name="payment_method"))
        self.sm.add_widget(Payment(name="payment"))
        self.sm.add_widget(PaymentWashcard(name="payment_washcard"))
        self.sm.add_widget(PaymentWashcardCardNotValid(name="payment_washcard_card_not_valid"))
        self.sm.add_widget(PaymentWashcardWrongCarwash(name="payment_washcard_wrong_carwash"))
        self.sm.add_widget(PaymentWashcardCardNotFound(name="payment_washcard_card_not_found"))
        self.sm.add_widget(PaymentWashcardInsufficientBalance(name="payment_washcard_insufficient_balance"))
        self.sm.add_widget(PaymentFailed(name="payment_failed"))
        self.sm.add_widget(PaymentSuccess(name="payment_success"))
        self.sm.add_widget(UpgradeWashcardReadCard(name="upgrade_washcard_read_card", settings=self.SETTINGS))
        self.sm.add_widget(UpgradeWashcardCredit(name="upgrade_washcard_credit"))
        self.sm.add_widget(UpgradeWashcardChooseAmount(name="upgrade_washcard_choose_amount"))
        self.sm.add_widget(UpgradeWashcardPayment(name="upgrade_washcard_payment"))
        self.sm.add_widget(UpgradeWashcardPaymentSuccess(name="upgrade_washcard_payment_success"))
        self.sm.add_widget(UpgradeWashcardPaymentFailed(name="upgrade_washcard_payment_failed"))
        self.sm.add_widget(Error(name="error"))
        self.sm.add_widget(InProgress(name="in_progress"))

    def load_settings(self):
        """loads settings from DB"""
        url = f'https://api.washterminalpro.nl/{API_PATH}/carwash'
        headers = {"Authorization": f'Bearer {self.jwt_token}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            response.raise_for_status()
        self.SETTINGS = json.loads(response.text)
        if "general" in self.SETTINGS:
            self.SETTINGS["general"]["jwtToken"] = self.jwt_token
            self.SETTINGS["general"]["carwashId"] = self.carwash_id
            self.buttonBackgroundColor = self.SETTINGS["general"]["buttonBackgroundColor"]
            self.buttonTextColor = self.SETTINGS["general"]["buttonTextColor"]
            self.backgroundColor = self.SETTINGS["general"]["backgroundColor"]
            Window.clearcolor = self.SETTINGS["general"]["backgroundColor"]  # Force window background to white
            self.textColor = self.SETTINGS["general"]["textColor"]
            self.supportPhone = self.SETTINGS["general"]["supportPhone"]
            Logger.setLevel(int(self.SETTINGS["general"]["logLevel"]))
            logging.basicConfig(encoding='utf-8', level=int(self.SETTINGS["general"]["logLevel"]))
        #logging.debug(self.SETTINGS)

    def selectProgram(self, program):
        logging.debug("Program selected: %s", str(program))
        order = Order(program, self.SETTINGS)
        self.activeOrder = order
        self.ga.start_new_session()
        items = [{ "item_id": str(program), "item_name": order.description, "item_brand": self.carwash_name, "item_category": order.transaction_type, "quantity": 1, "price": order.amount }]
        self.ga.send_event("add_to_cart", { "currency": "EUR", "value": order.margin, "items": items, "location": "Netherlands" })
        self.changeScreen("payment_method")

    def washcard_topup(self, amount):
        self.washcardTopup = amount
        self.ga.start_new_session()
        product_name = "TOPUP_" +str(amount)
        items = [{ "item_id": product_name, "item_name": product_name, "item_brand": self.carwash_name, "item_category": "TOPUP", "quantity": 1, "price": self.SETTINGS["prices"][product_name] }]
        self.ga.send_event("add_to_cart", { "currency": "EUR", "value": self.SETTINGS["margins"][product_name], "items": items, "location": "Netherlands" })

    def startMachine(self):
        # switch on status light
        if self.status_light:
            self.status_light.starting()
        # log with google analytics
        items = [{ "item_id": self.activeOrder.program, "item_name": self.activeOrder.description, "item_brand": self.carwash_name, "item_category": self.activeOrder.transaction_type, "quantity": 1, "price": self.activeOrder.amount }]
        self.ga.send_event("purchase", { "transaction_id": self.activeOrder.id, "currency": "EUR", "value": self.activeOrder.margin, "items": items, "location": "Netherlands" })
        #transform WASH_1 to 1
        programNumber = int(self.activeOrder.program[5:])
        binProgramNumber = '{0:04b}'.format(programNumber)
        logging.debug("Starting machine. Binary: %s", str(binProgramNumber))
        arr = list(binProgramNumber)
        print(arr)
        if int(arr[3]) == 1:
            pi.write(int(self.SETTINGS["gpio"]["BIT1LED"]),0)
        if int(arr[2]) == 1:
            pi.write(int(self.SETTINGS["gpio"]["BIT2LED"]),0)
        if int(arr[1]) == 1:
            pi.write(int(self.SETTINGS["gpio"]["BIT4LED"]),0)
        if int(arr[0]) == 1:
            pi.write(int(self.SETTINGS["gpio"]["BIT8LED"]),0)
        time.sleep(2)
        pi.write(int(self.SETTINGS["gpio"]["BIT1LED"]),1)
        pi.write(int(self.SETTINGS["gpio"]["BIT2LED"]),1)
        pi.write(int(self.SETTINGS["gpio"]["BIT4LED"]),1)
        pi.write(int(self.SETTINGS["gpio"]["BIT8LED"]),1)
        
        # track with google analytics
        self.ga.send_event("machine_start", { "program": self.activeOrder.program })

    def setupIO(self):
        try:
            if not pi.connected:
                exit()
            
            #status led setup
            if("statusLED_red" in self.SETTINGS["gpio"] and "statusLED_green" in self.SETTINGS["gpio"] and "statusLED_blue" in self.SETTINGS["gpio"]):
                rgb = [int(self.SETTINGS["gpio"]["statusLED_red"]), int(self.SETTINGS["gpio"]["statusLED_green"]), int(self.SETTINGS["gpio"]["statusLED_blue"])]
                self.status_light = Status_light(rgb)
            
            # Machine setup
            pi.set_mode(int(self.SETTINGS["gpio"]["BIT1LED"]), pigpio.OUTPUT)
            pi.set_mode(int(self.SETTINGS["gpio"]["BIT2LED"]), pigpio.OUTPUT)
            pi.set_mode(int(self.SETTINGS["gpio"]["BIT4LED"]), pigpio.OUTPUT)
            pi.set_mode(int(self.SETTINGS["gpio"]["BIT8LED"]), pigpio.OUTPUT)
            pi.write(int(self.SETTINGS["gpio"]["BIT1LED"]), 1)
            pi.write(int(self.SETTINGS["gpio"]["BIT2LED"]), 1)
            pi.write(int(self.SETTINGS["gpio"]["BIT4LED"]), 1)
            pi.write(int(self.SETTINGS["gpio"]["BIT8LED"]), 1)

            # Input setup
            pi.set_mode(int(self.SETTINGS["gpio"]["errorInput"]), pigpio.INPUT)
            pi.set_mode(int(self.SETTINGS["gpio"]["busyInput"]), pigpio.INPUT)
            pi.set_mode(int(self.SETTINGS["gpio"]["highVehicle"]), pigpio.INPUT)
            pi.set_mode(int(self.SETTINGS["gpio"]["stopVehicle"]), pigpio.INPUT)
            
            # check inputs
            logging.debug("STOP: %s", str(pi.read(int(self.SETTINGS["gpio"]["stopVehicle"]))))
            logging.debug("ERROR: %s", str(pi.read(int(self.SETTINGS["gpio"]["errorInput"]))))
            logging.debug("BUSY: %s", str(pi.read(int(self.SETTINGS["gpio"]["busyInput"]))))
            logging.debug("HIGH: %s", str(pi.read(int(self.SETTINGS["gpio"]["highVehicle"]))))

            #logging.debug("Inputs: %s %s %s" % (self.SETTINGS["gpio"]["errorInput"],self.SETTINGS["gpio"]["busyInput"],self.SETTINGS["gpio"]["highVehicle"]) )
            pi.set_pull_up_down(int(self.SETTINGS["gpio"]["errorInput"]), pigpio.PUD_DOWN)
            pi.set_pull_up_down(int(self.SETTINGS["gpio"]["busyInput"]), pigpio.PUD_DOWN)
            pi.set_pull_up_down(int(self.SETTINGS["gpio"]["highVehicle"]), pigpio.PUD_DOWN)
            pi.set_pull_up_down(int(self.SETTINGS["gpio"]["stopVehicle"]), pigpio.PUD_DOWN)

            # Machine in progress/done
            pi.callback(int(self.SETTINGS["gpio"]["busyInput"]), pigpio.EITHER_EDGE, self.busy_input_changed)
            pi.callback(int(self.SETTINGS["gpio"]["errorInput"]), pigpio.EITHER_EDGE, self.error_input_changed)
            pi.callback(int(self.SETTINGS["gpio"]["highVehicle"]), pigpio.EITHER_EDGE, self.high_input_changed)
            pi.callback(int(self.SETTINGS["gpio"]["stopVehicle"]), pigpio.EITHER_EDGE, self.stop_input_changed)
            
            #store statuses based on initial state of sensors
            self.busy = pi.read(int(self.SETTINGS["gpio"]["busyInput"]))
            self.high = pi.read(int(self.SETTINGS["gpio"]["highVehicle"]))
            self.error = pi.read(int(self.SETTINGS["gpio"]["errorInput"]))
            self.in_position = pi.read(int(self.SETTINGS["gpio"]["stopVehicle"]))

            logging.debug("GPIO setup completed successfully")

        except RuntimeError as e:
            logging.error("RuntimeError during GPIO setup: %s", e)
            pi.stop()
            raise

        except Exception as e:
            logging.error("Unexpected error during GPIO setup: %s", e)
            pi.stop()
            raise

    def clean_up(self):
        payment = self.sm.get_screen("payment")
        payment.cancel()
        pi.stop()

    @mainthread
    def changeScreen(self, screenName):
        logging.debug("Showing screen %s", screenName)
        self.ga.send_event("page_view", { "page_title": screenName, "location": "Netherlands", "firebase_screen": screenName, "firebase_screen_class": "python", "firebase_screen_id": screenName })
        logging.debug("Current screen:%s", str(self.sm.current))
        try:
            self.sm.current = screenName
        except ScreenManagerException as e:
            logging.error("Error changing screen:")
            logging.error(e)

    @mainthread
    def busy_input_changed(self):
        # only do something when value changes
        if self.busy != pi.read(int(self.SETTINGS["gpio"]["busyInput"])):
            logging.debug("Input changed: BUSY | value = %s", str(pi.read(int(self.SETTINGS["gpio"]["busyInput"]))))
            self.busy = pi.read(int(self.SETTINGS["gpio"]["busyInput"]))
            self.show_start_screen()

    @mainthread
    def error_input_changed(self):
        if self.error != pi.read(int(self.SETTINGS["gpio"]["errorInput"])):
            logging.debug("Input changed: ERROR | value = %s", str(pi.read(int(self.SETTINGS["gpio"]["errorInput"]))))
            self.error = pi.read(int(self.SETTINGS["gpio"]["errorInput"]))
            self.show_start_screen()

    @mainthread
    def high_input_changed(self):
        if self.high != pi.read(int(self.SETTINGS["gpio"]["highVehicle"])):
            logging.debug("Input changed: HIGH | value = %s", str(pi.read(int(self.SETTINGS["gpio"]["highVehicle"]))))
            self.high = pi.read(int(self.SETTINGS["gpio"]["highVehicle"]))
            # don't interrupt any other screens
            if self.sm.current == "program_selection" or self.sm.current == "program_selection_high":
                self.show_start_screen()

    @mainthread
    def stop_input_changed(self):
        if self.in_position != pi.read(int(self.SETTINGS["gpio"]["stopVehicle"])):
            logging.debug("Input changed: STOP | value = %s", str(pi.read(int(self.SETTINGS["gpio"]["stopVehicle"]))))
            self.in_position = pi.read(int(self.SETTINGS["gpio"]["stopVehicle"]))
            self.show_start_screen()

    @mainthread
    def show_start_screen(self):
        logging.debug("Determining start screen...")
        # ERROR
        if self.error != 1:
            if(self.status_light):
                self.status_light.error()
            self.changeScreen("error")
            return
        # BUSY
        if self.busy == 1:
            if(self.status_light):
                self.status_light.busy()
            self.changeScreen("in_progress")
            return
        # STOP
        if self.in_position != 1:
            if(self.status_light):
                self.status_light.stop()
            self.changeScreen("move_vehicle")
            return
        # HIGH
        if self.high == 1:
            if(self.status_light):
                self.status_light.high()
            self.changeScreen("program_selection_high")
            return
        # nothing special going on: turning off light
        if(self.status_light):
            self.status_light.off()
        self.changeScreen("program_selection")