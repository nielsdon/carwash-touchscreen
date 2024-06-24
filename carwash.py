import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'screens'))
from paymentFailed import PaymentFailed
from error import Error
from inProgress import InProgress
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
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from washingOrder import Order

import configparser
import pigpio
import locale
import logging
import time
import requests

from kivy.app import App
from kivy.clock import mainthread
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.uix.screenmanager import NoTransition, ScreenManager

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
    activeOrder = ''
    activeWashcard = ''
    washcardTopup = 0
    HIGH_VEHICLE = False
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
        response = requests.post(url, json={"username": API_TOKEN, "password": API_SECRET})
        if response.status_code != 200:
            response.raise_for_status()
            
        responseData = response.json()
        globals()['JWT_TOKEN'] = responseData["jwt"]
        globals()['CARWASH_ID'] = responseData["carwash_id"]
        self.loadSettings()
        
        # Setup window and screen manager
        Window.rotation = 90
        Window.show_cursor = False
        self.setupIO()

    def build(self):
        # Create and return the root widget (ScreenManager)
        self.sm = ScreenManager(transition=NoTransition())
        self.loadScreens()
        return self.sm    
      
    def loadScreens(self):
        # setup screens
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

    def loadSettings(self):
        url = f'https://api.washterminalpro.nl/{API_PATH}/carwash/{CARWASH_ID}/settings'
        headers = {"Authorization": f'Bearer {JWT_TOKEN}'}
        
        response = requests.get(url, headers=headers)
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
        print(self.SETTINGS)
        Logger.setLevel(int(self.SETTINGS["general"]["logLevel"]))
        logging.basicConfig(encoding='utf-8', level=int(self.SETTINGS["general"]["logLevel"]))
        
    def selectProgram(self, program):
        logging.debug("Program selected: %s", str(program))
        order = Order(program, self.SETTINGS)
        self.activeOrder = order
        self.changeScreen("payment_method")

    def startMachine(self):
        bin = '{0:04b}'.format(self.activeOrder.program)
        logging.debug("Starting machine. Binary: %s", str(bin))
        arr = list(bin)
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

    def setupIO(self):
        try:
            if not pi.connected:
                exit()
            # LED setup
            pi.set_mode(int(self.SETTINGS["gpio"]["errorLED"]), pigpio.OUTPUT)
            pi.set_mode(int(self.SETTINGS["gpio"]["progressLED"]), pigpio.OUTPUT)
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
            logging.debug("Inputs: %s %s %s" % (self.SETTINGS["gpio"]["errorInput"],self.SETTINGS["gpio"]["progressInput"],self.SETTINGS["gpio"]["highVehicle"]) )
            pi.set_pull_up_down(int(self.SETTINGS["gpio"]["errorInput"]), pigpio.PUD_UP)
            pi.set_pull_up_down(int(self.SETTINGS["gpio"]["progressInput"]), pigpio.PUD_DOWN)
            pi.set_pull_up_down(int(self.SETTINGS["gpio"]["highVehicle"]), pigpio.PUD_DOWN)

            # Machine in progress/done
            pi.callback(int(self.SETTINGS["gpio"]["progressInput"]), pigpio.EITHER_EDGE, self.progressStatusChanged)
            pi.callback(int(self.SETTINGS["gpio"]["errorInput"]), pigpio.EITHER_EDGE, self.errorStatusChanged)
            pi.callback(int(self.SETTINGS["gpio"]["highVehicle"]), pigpio.EITHER_EDGE, self.highVehicleStatusChanged)
            logging.debug("GPIO setup completed successfully")

        except RuntimeError as e:
            logging.error("RuntimeError during GPIO setup: %s", e)
            pi.stop()
            raise

        except Exception as e:
            logging.error("Unexpected error during GPIO setup: %s", e)
            pi.stop()
            raise
    def cleanUp(self):
        pi.stop()

    def changeScreen(self, screenName, *args):
        logging.debug("Showing screen %s", screenName)
        self.sm.current = screenName

    @mainthread
    def progressStatusChanged(self, *args):
        if pi.read(int(self.SETTINGS["gpio"]["progressInput"])):
            logging.debug("Machine in progress...")
            pi.write(int(self.SETTINGS["gpio"]["progressLED"]), 1)
            self.changeScreen("in_progress")
        else:
            logging.debug("Machine done!")
            pi.write(int(self.SETTINGS["gpio"]["progressLED"]), 0)
            # show program selection screen
            self.changeScreen("program_selection")

    @mainthread
    def errorStatusChanged(self, *args):
        if pi.read(int(self.SETTINGS["gpio"]["errorInput"])):
            logging.debug("Error resolved!")
            # switch on error led
            pi.write(int(self.SETTINGS["gpio"]["errorLED"]), 0)
            # show program selection screen
            self.changeScreen("program_selection")
        else:
            logging.debug("Error detected!")
            # switch on error led
            pi.write(int(self.SETTINGS["gpio"]["errorLED"]), 1)
            # show error screen
            self.changeScreen("error")

    @mainthread
    def highVehicleStatusChanged(self, *args):
        if pi.read(int(self.SETTINGS["gpio"]["highVehicle"])):
            logging.debug("High vehicle detected!")
            self.HIGH_VEHICLE = True
            # show program selection screen for high vehicles
            self.changeScreen("program_selection_high")
        else:
            logging.debug("High vehicle no longer detected")
            self.HIGH_VEHICLE = False
            # show normal program selection screen
            self.changeScreen("program_selection")
