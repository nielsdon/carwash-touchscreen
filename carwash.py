"""Carwash class"""
import sys
import os
import configparser
import locale
import logging
import time
import pigpio
import requests
from kivy.app import App
from kivy.clock import mainthread
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.uix.screenmanager import NoTransition, ScreenManager, ScreenManagerException
from washingOrder import Order
from googleAnalytics import GoogleAnalytics

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
CARWASH_ID = int(CONFIG.get('General', 'carwashId'))
API_TOKEN = str(CONFIG.get('General', 'apiToken'))
API_SECRET = str(CONFIG.get('General', 'apiSecret'))
TEST_MODE = bool(CONFIG.get('General', 'testMode') == 'True')
SETTINGS = {}
JWT_TOKEN = ''
pi = pigpio.pi()
if not pi.connected:
    exit() 
if TEST_MODE:
    API_PATH = 'dev'
else:
    API_PATH = 'v1'

locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')

class Carwash(App):
    """ class definition """
    activeOrder = ''
    activeWashcard = ''
    washcardTopup = 0
    HIGH_VEHICLE = False
    STOP_VEHICLE = False
    BUSY = False
    ERROR = True
    CARWASH_ID = 0
    TEST_MODE = True
    SETTINGS = {}
    buttonBackgroundColor = [1,1,1,1]
    buttonTextColor = [0,0,0,1]
    textColor = [0,0,0,1]
    backgroundColor = [1,1,1,1]
    supportPhone = ''

    def __init__(self, **kwargs):
        super(Carwash, self).__init__(**kwargs)
        # Init globals
        self.TEST_MODE = TEST_MODE
        self.CARWASH_ID = CARWASH_ID

        # Initialize API connection and settings
        url = f'https://api.washterminalpro.nl/{API_PATH}/login/'
        response = requests.post(url, json={"username": API_TOKEN, "password": API_SECRET}, timeout=10)
        if response.status_code != 200:
            response.raise_for_status()

        responseData = response.json()
        globals()['JWT_TOKEN'] = responseData["jwt"]
        globals()['CARWASH_ID'] = responseData["carwash_id"]
        self.load_settings()

        # Setup window and screen manager
        Window.rotation = 90
        Window.show_cursor = False
        self.setupIO()
        
        # Setup Google Analytics
        self.ga = GoogleAnalytics()
        
        self.sm = None

    def build(self):
        # Create and return the root widget (ScreenManager)
        self.sm = ScreenManager(transition=NoTransition())
        self.load_screens()
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
        url = f'https://api.washterminalpro.nl/{API_PATH}/carwash/{CARWASH_ID}/settings'
        headers = {"Authorization": f'Bearer {JWT_TOKEN}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            response.raise_for_status()
        #print(response.json())
        self.SETTINGS = response.json()
        if "general" in self.SETTINGS:
            self.SETTINGS["general"]["jwtToken"] = JWT_TOKEN
            self.SETTINGS["general"]["carwashId"] = CARWASH_ID
            self.buttonBackgroundColor = self.SETTINGS["general"]["buttonBackgroundColor"]
            self.buttonTextColor = self.SETTINGS["general"]["buttonTextColor"]
            self.backgroundColor = self.SETTINGS["general"]["backgroundColor"]
            self.textColor = self.SETTINGS["general"]["textColor"]
            self.supportPhone = self.SETTINGS["general"]["supportPhone"]
        Logger.setLevel(int(self.SETTINGS["general"]["logLevel"]))
        logging.basicConfig(encoding='utf-8', level=int(self.SETTINGS["general"]["logLevel"]))
        logging.debug(self.SETTINGS)
        
    def selectProgram(self, program):
        logging.debug("Program selected: %s", str(program))
        order = Order(program, self.SETTINGS)
        self.activeOrder = order
        self.ga.start_new_session()
        items = [{ "item_id": order.id, "item_name": order.program, "item_brand": CARWASH_ID, "item_category": order.transaction_type, "quantity": 1, "price": order.amount }]
        self.ga.send_event("add_to_cart", { "currency": "EUR", "value": order.amount, "items": items })
        self.changeScreen("payment_method")

    def startMachine(self):
        # log with google analytics
        items = [{ "item_id": self.activeOrder.id, "item_name": self.activeOrder.program, "item_brand": CARWASH_ID, "item_category": self.activeOrder.transaction_type, "quantity": 1, "price": self.activeOrder.amount }]
        self.ga.send_event("purchase", { "transaction_id": self.activeOrder.id, "currency": "EUR", "value": self.activeOrder.amount, "items": items })
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
            pi.callback(int(self.SETTINGS["gpio"]["busyInput"]), pigpio.EITHER_EDGE, self.show_start_screen)
            pi.callback(int(self.SETTINGS["gpio"]["errorInput"]), pigpio.EITHER_EDGE, self.show_start_screen)
            pi.callback(int(self.SETTINGS["gpio"]["highVehicle"]), pigpio.EITHER_EDGE, self.show_start_screen)
            pi.callback(int(self.SETTINGS["gpio"]["stopVehicle"]), pigpio.EITHER_EDGE, self.show_start_screen)
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
    def changeScreen(self, screenName, *args):
        logging.debug("Showing screen %s", screenName)
        self.ga.send_event("page_view", { "page_title": screenName })
        try:
            self.sm.current = screenName
        except ScreenManagerException as e:
            logging.error("Error changing screen:")
            logging.error(e)

    @mainthread
    def show_start_screen(self, *args):
        logging.debug("Determining start screen...")
        if pi.read(int(self.SETTINGS["gpio"]["errorInput"])) != 1:
            self.changeScreen("error")
            return True
        if pi.read(int(self.SETTINGS["gpio"]["busyInput"])) == 1:
            self.changeScreen("in_progress")
            return True
        if pi.read(int(self.SETTINGS["gpio"]["stopVehicle"])) != 1:
            self.changeScreen("move_vehicle")
            return True
        if pi.read(int(self.SETTINGS["gpio"]["highVehicle"])) == 1:
            self.changeScreen("program_selection_high")
            return True
        self.changeScreen("program_selection")