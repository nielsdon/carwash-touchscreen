"""Carwash class"""
import sys
import os
import locale
import logging
import time
import netifaces
import pigpio

from kivy.app import App
from kivy.clock import mainthread
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.uix.screenmanager import NoTransition, ScreenManager, ScreenManagerException
from kivy.core.text import LabelBase
from washingOrder import Order
from auth_client import AuthClient
from google_analytics import GoogleAnalytics
from telegraf_logger import TelegrafLogger
from state_tracker import StateTracker
from dotenv import load_dotenv

from screens.paymentFailed import PaymentFailed
from screens.error import Error
from screens.inProgress import InProgress
from screens.finished import Finished
from screens.moveVehicle import MoveVehicle
from screens.payment import Payment
from screens.paymentMethod import PaymentMethod
from screens.paymentSuccess import PaymentSuccess
from screens.paymentWashcard import PaymentWashcard
from screens.paymentWashcardCardNotFound import PaymentWashcardCardNotFound
from screens.paymentWashcardCardNotValid import PaymentWashcardCardNotValid
from screens.paymentWashcardInsufficientBalance import PaymentWashcardInsufficientBalance
from screens.paymentWashcardWrongCarwash import PaymentWashcardWrongCarwash
from screens.programSelection import ProgramSelection
from screens.programSelectionHigh import ProgramSelectionHigh
from screens.upgradeWashcardChooseAmount import UpgradeWashcardChooseAmount
from screens.upgradeWashcardPayment import UpgradeWashcardPayment
from screens.upgradeWashcardCredit import UpgradeWashcardCredit
from screens.upgradeWashcardPaymentFailed import UpgradeWashcardPaymentFailed
from screens.upgradeWashcardPaymentSuccess import UpgradeWashcardPaymentSuccess
from screens.upgradeWashcardReadCard import UpgradeWashcardReadCard

os.environ['KIVY_NO_FILELOG'] = '1'  # eliminate file log

# Load environment variables from .env file
load_dotenv()

API_TOKEN = os.getenv("CLIENT_ID")
API_SECRET = os.getenv("CLIENT_SECRET")
TEST_MODE = bool(os.getenv("TEST_MODE") == '1')

SETTINGS = {}

# Get environment variables
pigpio_addr = os.getenv('PIGPIO_ADDR', 'localhost')  # Default to 'localhost' if the env var is not set
pigpio_port = int(os.getenv('PIGPIO_PORT', 8888))    # Default to 8888 if the env var is not set

# Connect to pigpiod
pi = pigpio.pi(pigpio_addr, pigpio_port)

if not pi.connected:
    print("Failed to connect to pigpiod")
else:
    print("Connected to pigpiod")

if TEST_MODE:
    API_URL = "https://api.washterminalpro.nl/dev"
    os.environ['KIVY_NO_CONSOLELOG'] = '1'  # Enable console logging
    os.environ['KIVY_LOG_LEVEL'] = 'debug'  # Set log level to debug
else:
    API_URL = "https://api.washterminalpro.nl/v1"
    os.environ['KIVY_NO_CONSOLELOG'] = '0'  # Enable console logging
    os.environ['KIVY_LOG_LEVEL'] = 'error'  # Set log level to error

locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')
# Register the custom font
LabelBase.register(name="DefaultFont", fn_regular="InstrumentSans-VariableFont_wdth.ttf")
# print("Registered fonts:", LabelBase._fonts)  # Prints all registered fonts


class Carwash(App):
    """ class definition """
    activeOrder = ''
    activeWashcard = ''
    washcardTopup = 0
    carwash_id = 0
    jwt_token = ''
    TEST_MODE = True
    SETTINGS = {}
    buttonBackgroundColor = "#9BC6B9"
    backgroundColor = "#E3EEEB"
    buttonTextColor = "#FFFFFF"
    textColor = "#000000"
    backgroundColor = "#9BC6B9"
    supportPhone = ''
    in_position = 0
    error = 1
    high = 0
    busy = 0
    status_light = None
    carwash_name = ''

    def __init__(self, SETTINGS=None, **kwargs):
        super(Carwash, self).__init__(**kwargs)
        self.SETTINGS = SETTINGS or {}        # Init globals
        self.TEST_MODE = TEST_MODE

        # Get the IP address
        self.ip_address = self.get_ip_address()

        # Initialize AuthClient for managing authentication
        if self.TEST_MODE:
            token_url = 'https://auth-dev.washterminalpro.nl/token'
        else:
            token_url = 'https://auth.washterminalpro.nl/token'

        self.auth_client = AuthClient(API_TOKEN, API_SECRET, token_url)
        if self.SETTINGS == {}:
            self.load_settings()

        # initialize trackers
        self.init_trackers()

        # Setup window and screen manager
        Window.rotation = 90
        Window.show_cursor = False
        self.setupIO()
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
        # Use the custom font globally
        self.theme_cls = {
            "font_name": "DefaultFont"
        }
        self.sm = ScreenManager(transition=NoTransition())
        self.load_screens()
        # show the test label with IP address in test mode
        screen = self.sm.get_screen("program_selection")
        screenHigh = self.sm.get_screen("program_selection_high")
        if "programSelectionText" in self.SETTINGS["general"]:
            screen.ids.welcome_text.text = self.SETTINGS["general"]["programSelectionText"]
            screenHigh.ids.welcome_text.text = self.SETTINGS["general"]["programSelectionText"]
        if self.TEST_MODE:
            screen.ids.test_label.text = "TEST - " + self.ip_address
            screenHigh.ids.test_label.text = "TEST - " + self.ip_address
        # start operation
        self.show_start_screen()
        return self.sm

    def load_screens(self):
        """ setup screens"""
        self.sm.add_widget(MoveVehicle(name="move_vehicle"))
        self.sm.add_widget(ProgramSelection(name="program_selection",
                                            settings=self.SETTINGS))
        self.sm.add_widget(ProgramSelectionHigh(name="program_selection_high",
                                                settings=self.SETTINGS))
        self.sm.add_widget(PaymentMethod(name="payment_method"))
        self.sm.add_widget(Payment(name="payment"))
        self.sm.add_widget(PaymentWashcard(name="payment_washcard"))
        self.sm.add_widget(PaymentWashcardCardNotValid(name="payment_washcard_card_not_valid"))
        self.sm.add_widget(PaymentWashcardWrongCarwash(name="payment_washcard_wrong_carwash"))
        self.sm.add_widget(PaymentWashcardCardNotFound(name="payment_washcard_card_not_found"))
        self.sm.add_widget(PaymentWashcardInsufficientBalance(
            name="payment_washcard_insufficient_balance"))
        self.sm.add_widget(PaymentFailed(name="payment_failed"))
        self.sm.add_widget(PaymentSuccess(name="payment_success"))
        self.sm.add_widget(UpgradeWashcardReadCard(name="upgrade_washcard_read_card",
                                                   settings=self.SETTINGS))
        self.sm.add_widget(UpgradeWashcardCredit(name="upgrade_washcard_credit"))
        self.sm.add_widget(UpgradeWashcardChooseAmount(name="upgrade_washcard_choose_amount"))
        self.sm.add_widget(UpgradeWashcardPayment(name="upgrade_washcard_payment"))
        self.sm.add_widget(UpgradeWashcardPaymentSuccess(name="upgrade_washcard_payment_success"))
        self.sm.add_widget(UpgradeWashcardPaymentFailed(name="upgrade_washcard_payment_failed"))
        self.sm.add_widget(Error(name="error"))
        self.sm.add_widget(InProgress(name="in_progress"))
        self.sm.add_widget(Finished(name="finished"))

    def load_settings(self):
        """Load initial carwash details using AuthClient for authentication."""
        url = f'{API_URL}/carwash'
        try:
            _, data = self.auth_client.make_authenticated_request(url)
        except Exception as e:
            print(f"Unexpected Error: {e}")
            return
        self.carwash_id = data["id"]
        self.carwash_name = data["name"]
        self.SETTINGS = data["settings"]

        if "general" in self.SETTINGS:
            self.SETTINGS["general"]["carwashId"] = self.carwash_id
            if "buttonBackgroundColor" in self.SETTINGS["general"]:
                self.buttonBackgroundColor = self.SETTINGS["general"]["buttonBackgroundColor"]
            if "buttonTextColor" in self.SETTINGS["general"]:
                self.buttonTextColor = self.SETTINGS["general"]["buttonTextColor"]
            if "backgroundColor" in self.SETTINGS["general"]:
                self.backgroundColor = self.SETTINGS["general"]["backgroundColor"]
            if "textColor" in self.SETTINGS["general"]:
                self.textColor = self.SETTINGS["general"]["textColor"]
            Window.clearcolor = self.backgroundColor
            self.supportPhone = self.SETTINGS["general"]["supportPhone"]
            Logger.setLevel(int(self.SETTINGS["general"]["logLevel"]))
            logging.basicConfig(encoding='utf-8', level=int(self.SETTINGS["general"]["logLevel"]))

    def init_trackers(self):
        # Initialize the Google Analytics Logger
        if TEST_MODE:
            measurement_id = os.getenv('GA4_MEASUREMENT_ID_DEV')
        else:
            measurement_id = os.getenv('GA4_MEASUREMENT_ID_PROD')

        api_secret = os.getenv('GA4_API')
        client_id = os.getenv('CLIENT_ID')
        ga_logger = GoogleAnalytics(measurement_id, api_secret, client_id)

        # Initialize the Telegraf Logger
        telegraf_logger = TelegrafLogger(
            telegraf_url="http://localhost:8080/telegraf"
        )

        self.tracker = StateTracker(ga_logger, telegraf_logger)

    def select_program(self, program):
        """" function that is called from the program-selection screens """
        logging.debug("Program selected: %s", str(program))
        order = Order(program, self.SETTINGS)
        self.activeOrder = order
        self.tracker.add_to_cart({
            "item_id": str(program),
            "item_name": order.description,
            "item_brand": self.carwash_name,
            "item_category": order.transaction_type,
            "quantity": 1,
            "price": order.amount
        })
        # progress to next screen
        if 'paynl' in self.SETTINGS:
            # only show payment selection when a terminal is available
            self.change_screen("payment_method")
        else:
            # otherwise, just pay with a washcard
            self.change_screen("payment_washcard")

    def washcard_topup(self, amount):
        """" function to handle the card topups """
        self.washcardTopup = amount
        productName = "TOPUP_" + str(amount)
        self.tracker.add_to_cart({
            "item_id": productName,
            "item_name": productName,
            "item_brand": self.carwash_name,
            "item_category": "TOPUP",
            "quantity": 1,
            "price": self.SETTINGS["prices"][productName]
        })

    def startMachine(self):
        """ method to physically switch on the machine with the selected program """
        # transform WASH_1 to 1
        programNumber = int(self.activeOrder.program[5:])
        binProgramNumber = '{0:04b}'.format(programNumber)
        logging.debug("Starting machine. Binary: %s", str(binProgramNumber))
        arr = list(binProgramNumber)
        print(arr)
        if int(arr[3]) == 1:
            pi.write(int(self.SETTINGS["gpio"]["BIT1LED"]), 0)
        if int(arr[2]) == 1:
            pi.write(int(self.SETTINGS["gpio"]["BIT2LED"]), 0)
        if int(arr[1]) == 1:
            pi.write(int(self.SETTINGS["gpio"]["BIT4LED"]), 0)
        if int(arr[0]) == 1:
            pi.write(int(self.SETTINGS["gpio"]["BIT8LED"]), 0)
        time.sleep(2)
        pi.write(int(self.SETTINGS["gpio"]["BIT1LED"]), 1)
        pi.write(int(self.SETTINGS["gpio"]["BIT2LED"]), 1)
        pi.write(int(self.SETTINGS["gpio"]["BIT4LED"]), 1)
        pi.write(int(self.SETTINGS["gpio"]["BIT8LED"]), 1)

        # track event
        self.tracker.set_page(self.sm.current, start_machine=1, busy=self.busy, high_vehicle=self.high, error=self.error, stop=self.in_position)

        # track purchase
        self.tracker.purchase({
            "transaction_id": self.activeOrder.id
        })

    def setupIO(self):
        """ setup GPIO ports based on the carwash settings """
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

            pi.set_pull_up_down(int(self.SETTINGS["gpio"]["errorInput"]), pigpio.PUD_DOWN)
            pi.set_pull_up_down(int(self.SETTINGS["gpio"]["busyInput"]), pigpio.PUD_DOWN)
            pi.set_pull_up_down(int(self.SETTINGS["gpio"]["highVehicle"]), pigpio.PUD_DOWN)
            pi.set_pull_up_down(int(self.SETTINGS["gpio"]["stopVehicle"]), pigpio.PUD_DOWN)

            # check inputs
            logging.debug("STOP: %s", str(pi.read(int(self.SETTINGS["gpio"]["stopVehicle"]))))
            logging.debug("ERROR: %s", str(pi.read(int(self.SETTINGS["gpio"]["errorInput"]))))
            logging.debug("BUSY: %s", str(pi.read(int(self.SETTINGS["gpio"]["busyInput"]))))
            logging.debug("HIGH: %s", str(pi.read(int(self.SETTINGS["gpio"]["highVehicle"]))))

            # Machine in progress/done
            pi.callback(int(self.SETTINGS["gpio"]["busyInput"]),
                        pigpio.EITHER_EDGE, self.busy_input_changed)
            pi.callback(int(self.SETTINGS["gpio"]["errorInput"]),
                        pigpio.EITHER_EDGE, self.error_input_changed)
            pi.callback(int(self.SETTINGS["gpio"]["highVehicle"]),
                        pigpio.EITHER_EDGE, self.high_input_changed)
            pi.callback(int(self.SETTINGS["gpio"]["stopVehicle"]),
                        pigpio.EITHER_EDGE, self.stop_input_changed)

            # store statuses based on initial state of sensors
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
        """ kill threads when app shuts down """
        payment = self.sm.get_screen("payment")
        payment.cancel()
        pi.stop()

    @mainthread
    def change_screen(self, screen_name):
        """ main function to switch screens """
        logging.debug("Current screen: %s", str(self.sm.current))
        logging.debug("Switching to screen %s", screen_name)

        try:
            self.sm.current = screen_name
            self.tracker.set_page(self.sm.current, busy=self.busy, high_vehicle=self.high, error=self.error, stop=self.in_position)
        except ScreenManagerException as e:
            logging.error("Error changing screen:")
            logging.error(e)

    @mainthread
    def busy_input_changed(self, *_):
        """" input gpio value changed on busy pin """
        # only do something when value changes
        if self.busy != pi.read(int(self.SETTINGS["gpio"]["busyInput"])):
            logging.debug("Input changed: BUSY | value = %s",
                          str(pi.read(int(self.SETTINGS["gpio"]["busyInput"]))))
            # washing has finished: show finish screen
            self.busy = pi.read(int(self.SETTINGS["gpio"]["busyInput"]))
            # track state change
            self.tracker.set_page(self.sm.current, busy=self.busy, high_vehicle=self.high, error=self.error, stop=self.in_position)
            if self.busy == 0:
                self.change_screen("finished")
            else:
                self.show_start_screen()

    @mainthread
    def error_input_changed(self, *_):
        """" input gpio value changed on error pin """
        if self.error != pi.read(int(self.SETTINGS["gpio"]["errorInput"])):
            logging.debug("Input changed: ERROR | value = %s", str(pi.read(int(self.SETTINGS["gpio"]["errorInput"]))))
            self.error = pi.read(int(self.SETTINGS["gpio"]["errorInput"]))
            # track state change
            self.tracker.set_page(self.sm.current, busy=self.busy, high_vehicle=self.high, error=self.error, stop=self.in_position)
            self.show_start_screen()

    @mainthread
    def high_input_changed(self, *_):
        """" input gpio value changed on high input pin """
        if self.high != pi.read(int(self.SETTINGS["gpio"]["highVehicle"])):
            logging.debug("Input changed: HIGH | value = %s",
                          str(pi.read(int(self.SETTINGS["gpio"]["highVehicle"]))))
            self.high = pi.read(int(self.SETTINGS["gpio"]["highVehicle"]))
            # track state change
            self.tracker.set_page(self.sm.current, busy=self.busy, high_vehicle=self.high, error=self.error, stop=self.in_position)
            # don't interrupt any other screens
            if self.sm.current in ["program_selection", "program_selection_high"]:
                self.show_start_screen()

    @mainthread
    def stop_input_changed(self, *_):
        """" input gpio value changed on stop input pin """
        if self.in_position != pi.read(int(self.SETTINGS["gpio"]["stopVehicle"])):
            logging.debug("Input changed: STOP | value = %s",
                          str(pi.read(int(self.SETTINGS["gpio"]["stopVehicle"]))))
            self.in_position = pi.read(int(self.SETTINGS["gpio"]["stopVehicle"]))
            # track state change
            self.tracker.set_page(self.sm.current, busy=self.busy, high_vehicle=self.high, error=self.error, stop=self.in_position)
            self.show_start_screen()

    @mainthread
    def show_start_screen(self, *_):
        """ determine and show the start screen based on state of input pins """
        logging.debug("Determining start screen...")
        # ERROR
        if self.error != 1:
            self.change_screen("error")
            return
        # BUSY
        if self.busy == 1:
            self.change_screen("in_progress")
            return
        # STOP
        if self.in_position != 1:
            self.change_screen("move_vehicle")
            return
        # HIGH
        if self.high == 1:
            self.change_screen("program_selection_high")
            return
        self.change_screen("program_selection")


if __name__ == '__main__':
    # Only exit when the script is run directly, not when imported
    print("Running carwash.py directly")
    sys.exit()
