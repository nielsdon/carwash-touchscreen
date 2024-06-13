"""The Main application for the touchscreen"""
import configparser
import locale
import logging
import os
import signal
import sys
import time
import requests
import pigpio
from functools import partial
from decimal import Decimal

#import RPi.GPIO as GPIO # type: ignore
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.uix.button import Button

from payNL import PayNL
from washcard import Washcard
from washingOrder import Order

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

class ProgramSelection(Screen):
    def __init__(self, **kwargs):
        super(ProgramSelection, self).__init__(**kwargs)
        app = App.get_running_app()
        layout = self.ids.selectionLayout
        for idx, data in enumerate(SETTINGS["prices"], start=0):
            if(data.__contains__('WASH')):
                counter = idx + 1
                btn = Button(text="Wasprogramma %s" % str(counter), background_color=[0.21,0.69,0.94,1], font_size="42sp", color=[1,1,1,1])
                btn.bind(on_release=lambda instance: self.selectProgram(counter))
                layout.add_widget(btn)
        btn = Button(text="Waspas opwaarderen", background_color=[0.21,0.69,0.94,1], font_size="42sp", color=[1,1,1,1])
        btn.bind(on_release=lambda instance: self.upgradeWashcard())
        layout.add_widget(btn)
        
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Program selection ===")
        # You can optionally call the superclass's method if needed
        super().on_enter(*args, **kwargs)
        app = App.get_running_app()
        # Make sure the selection for high vehicles is shown when returning to program selection
        if app.HIGH_VEHICLE:
            logging.debug("High vehicle detected!")
            # show program selection screen for high vehicles
            app.changeScreen("program_selection_high")

    def selectProgram(self, program):
        app = App.get_running_app()
        app.selectProgram(program)

    def upgradeWashcard(self):
        app = App.get_running_app()
        app.changeScreen("upgrade_washcard_read_card")


class ProgramSelectionHigh(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Program selection for high vehicles ===")
        super().on_enter(*args, **kwargs)

    def selectProgram(self, program):
        app = App.get_running_app()
        app.selectProgram(program)

    def upgradeWashcard(self):
        app = App.get_running_app()
        app.changeScreen("upgrade_washcard_read_card")


class PaymentMethod(Screen):
    def selectPin(self):
        app = App.get_running_app()
        app.changeScreen('payment')

    def selectWashcard(self):
        app = App.get_running_app()
        app.changeScreen('payment_washcard')

    def cancel(self):
        app = App.get_running_app()
        app.changeScreen('program_selection')
        
class PaymentWashcard(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Payment with washcard ===")
        app = App.get_running_app()
        washcard = Washcard(SETTINGS)
        washcard.readCard()
        if washcard.uid == '':
            app.changeScreen('payment_washcard_card_not_found')
        elif washcard.carwash == '':
            app.changeScreen('payment_washcard_card_not_valid')
        elif int(washcard.carwash.id) != CARWASH_ID:
            logging.debug("Washcard carwash_id: %s", str(washcard.carwash.id))
            logging.debug("Config carwash_id: %s", str(CARWASH_ID))
            screen = app.sm.get_screen('payment_washcard_wrong_carwash')
            screen.ids.lbl_carwash.text = washcard.carwash.name + '\n' + washcard.carwash.city
            app.changeScreen('payment_washcard_wrong_carwash')
        else:
            #checks done: create transaction
            response = washcard.pay(app.activeOrder)
            logging.debug('Response status code: %s', str(response["statusCode"]))
            if response["statusCode"] == 200:
                screen = app.sm.get_screen('payment_success')
                logging.debug('New balance: %s %s',  locale.LC_MONETARY, locale.currency(float(response["balance"])))
                screen.ids.lbl_balance.text = locale.currency(float(response["balance"]))
                app.changeScreen('payment_success')
            elif response["statusCode"] == 462:
                screen = app.sm.get_screen('payment_washcard_insufficient_balance')
                screen.ids.lbl_balance.text = locale.currency(float(washcard.balance))
                app.changeScreen('payment_washcard_insufficient_balance')
            elif response["statusCode"] == 460:
                app.changeScreen('payment_washcard_card_not_valid')
            else:
                app.changeScreen('payment_failed')



class Payment(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Payment ===")
        app = App.get_running_app()

        # pay.nl communicatie: start transaction
        pay = PayNL(SETTINGS)
        transactionId = pay.payOrder(app.activeOrder)
        logging.debug("TransactionId: %s", transactionId)

        # pay.nl communicatie: check order status
        transactionStatus = 'PENDING'
        wait = 0
        while transactionStatus == 'PENDING' and wait < 20 and transactionId:
            transactionStatus = pay.getTransactionStatus(transactionId)
            logging.debug("TransactionStatus: %s", transactionStatus)
            time.sleep(2)
            wait += 1

        # timeout is reached or status is no longer PENDING
        if transactionStatus == 'PAID':
            logging.debug('betaling gelukt!')
            app.changeScreen('payment_success')
        else:
            logging.debug('fout bij betaling')
            pay.cancelTransaction(transactionId)
            app.changeScreen('payment_failed')


class InProgress(Screen):
    pass

class PaymentFailed(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Payment failed ===")
        app = App.get_running_app()
        app.activeOrder = ''
        Clock.schedule_once(partial(app.changeScreen, "program_selection"), 5)


class PaymentSuccess(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Payment success ===")
        app = App.get_running_app()
        app.startMachine()
        if TEST_MODE:
            time.sleep(3)
            app.changeScreen('program_selection')


class PaymentWashcardWrongCarwash(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Wrong Carwash ===")
        app = App.get_running_app()
        time.sleep(6)
        app.changeScreen('program_selection')


class PaymentWashcardCardNotValid(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Washcard not valid ===")
        app = App.get_running_app()
        time.sleep(3)
        app.changeScreen('program_selection')


class PaymentWashcardCardNotFound(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== No Washcard found ===")
        app = App.get_running_app()
        time.sleep(3)
        app.changeScreen('program_selection')


class PaymentWashcardInsufficientBalance(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Insufficient balance on washcard ===")
        app = App.get_running_app()
        time.sleep(3)
        app.changeScreen('program_selection')


class Error(Screen):
    pass


class UpgradeWashcardReadCard(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Upgrade washcard - read card ===")
        app = App.get_running_app()
        washcard = Washcard(SETTINGS)
        washcard.readCard()
        if washcard.uid == '':
            app.changeScreen('payment_washcard_card_not_found')
        elif washcard.carwash == '':
            app.changeScreen('payment_washcard_card_not_valid')
        elif int(washcard.carwash.id) != CARWASH_ID:
            logging.debug('Washcard carwash_id: %s', str(washcard.carwash.id))
            logging.debug('Config carwash_id: %s', CARWASH_ID)
            screen = app.sm.get_screen('payment_washcard_wrong_carwash')
            screen.ids.lbl_carwash.text = washcard.carwash.name + '\n' + washcard.carwash.city
            app.changeScreen('payment_washcard_wrong_carwash')
        else:
            screen = app.sm.get_screen('upgrade_washcard_choose_amount')
            screen.ids.lbl_balance.text = locale.currency(
                float(washcard.balance))
            screen.ids.lbl_carwash.text = washcard.carwash.name + ' - ' + washcard.carwash.city
            screen.ids.lbl_company.text = washcard.company.name + ' - ' + washcard.carwash.city
            app.activeWashcard = washcard
            app.changeScreen('upgrade_washcard_choose_amount')


class UpgradeWashcardChooseAmount(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Upgrade Washcard - Choose Amount ===")

    def chooseAmount(self, amount):
        logging.debug("=== Selected amount: %s", str(amount))
        app = App.get_running_app()
        app.washcardTopup = amount
        app.changeScreen("upgrade_washcard_payment")

    def cancel(self):
        app = App.get_running_app()
        app.changeScreen("program_selection")


class UpgradeWashcardPayment(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Upgrade washcard - payment ===")
        app = App.get_running_app()
        logging.debug(app.activeWashcard.uid)
        logging.debug(str(app.washcardTopup))

        # pay.nl communicatie: start transaction
        pay = PayNL(SETTINGS)
        transactionId = pay.payCardUpgrade(
            app.washcardTopup, app.activeWashcard)
        logging.debug("TransactionId: %s", transactionId)

        # pay.nl communicatie: check order status
        transactionStatus = 'PENDING'
        wait = 0
        while transactionStatus == 'PENDING' and wait < 20 and transactionId:
            transactionStatus = pay.getTransactionStatus(transactionId)
            logging.debug("TransactionStatus: %s", transactionStatus)
            time.sleep(2)
            wait += 1

        # timeout is reached or status is no longer PENDING
        if transactionStatus == 'PAID':
            logging.debug('payment success!')
            app.changeScreen('upgrade_washcard_payment_success')
        else:
            logging.debug('payment error')
            pay.cancelTransaction(transactionId)
            app.changeScreen('upgrade_washcard_payment_failed')


class UpgradeWashcardPaymentSuccess(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Upgrade washcard - payment success ===")
        app = App.get_running_app()
        card = app.activeWashcard
        card.upgrade(app.washcardTopup)
        time.sleep(5)
        app.activeWashcard = ''
        app.washcardTopup = ''
        app.changeScreen("program_selection")


class UpgradeWashcardPaymentFailed(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Upgrade washcard - payment failed ===")
        app = App.get_running_app()
        app.activeWashcard = ''
        app.washcardTopup = ''
        time.sleep(5)
        app.changeScreen("program_selection")


class Carwash(App):
    activeOrder = ''
    activeWashcard = ''
    washcardTopup = 0
    HIGH_VEHICLE = False

    def build(self):
        url = f'https://api.washterminalpro.nl/{API_PATH}/login/'
        response = requests.post(url, json={"username": API_TOKEN, "password": API_SECRET})
        if response.status_code != 200:
            response.raise_for_status()
            
        responseData = response.json()
        globals()['JWT_TOKEN'] = responseData["jwt"]
        globals()['CARWASH_ID'] = responseData["carwash_id"]
        self.loadSettings()
        Window.rotation = 90  # Rotate the window 90 degrees
        Window.show_cursor = False
        # setup the screens
        Builder.load_file('screens.kv')

        # setup screens
        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(ProgramSelection(name="program_selection"))
        self.sm.add_widget(ProgramSelectionHigh(name="program_selection_high"))
        self.sm.add_widget(PaymentMethod(name="payment_method"))
        self.sm.add_widget(Payment(name="payment"))
        self.sm.add_widget(PaymentWashcard(name="payment_washcard"))
        self.sm.add_widget(PaymentWashcardCardNotValid(name="payment_washcard_card_not_valid"))
        self.sm.add_widget(PaymentWashcardWrongCarwash(name="payment_washcard_wrong_carwash"))
        self.sm.add_widget(PaymentWashcardCardNotFound(name="payment_washcard_card_not_found"))
        self.sm.add_widget(PaymentWashcardInsufficientBalance(name="payment_washcard_insufficient_balance"))
        self.sm.add_widget(PaymentFailed(name="payment_failed"))
        self.sm.add_widget(PaymentSuccess(name="payment_success"))
        self.sm.add_widget(UpgradeWashcardReadCard(name="upgrade_washcard_read_card"))
        self.sm.add_widget(UpgradeWashcardChooseAmount(name="upgrade_washcard_choose_amount"))
        self.sm.add_widget(UpgradeWashcardPayment(name="upgrade_washcard_payment"))
        self.sm.add_widget(UpgradeWashcardPaymentSuccess(name="upgrade_washcard_payment_success"))
        self.sm.add_widget(UpgradeWashcardPaymentFailed(name="upgrade_washcard_payment_failed"))
        self.sm.add_widget(Error(name="error"))
        self.sm.add_widget(InProgress(name="in_progress"))
        # setup leds
        self.setupIO()
        return self.sm

    def loadSettings(self):
        url = f'https://api.washterminalpro.nl/{API_PATH}/carwash/{CARWASH_ID}/settings'
        headers = {"Authorization": f'Bearer {JWT_TOKEN}'}
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            response.raise_for_status()
        #print(response.json())
        globals()['SETTINGS'] = response.json()
        SETTINGS["general"]["jwtToken"] = JWT_TOKEN
        SETTINGS["general"]["carwashId"] = CARWASH_ID
        print(SETTINGS)
        Logger.setLevel(int(SETTINGS["general"]["logLevel"]))
        logging.basicConfig(encoding='utf-8', level=int(SETTINGS["general"]["logLevel"]))
        
    def selectProgram(self, program):
        logging.debug("Program selected: %s", str(program))
        order = Order(program, SETTINGS)
        self.activeOrder = order
        self.changeScreen("payment_method")

    def startMachine(self):
        bin = '{0:04b}'.format(self.activeOrder.program)
        logging.debug("Starting machine. Binary: %s", str(bin))
        arr = list(bin)
        print(arr)
        if int(arr[3]) == 1:
            pi.write(int(SETTINGS["gpio"]["BIT1LED"]), 1)
        if int(arr[2]) == 1:
            pi.write(int(SETTINGS["gpio"]["BIT2LED"]), 1)
        if int(arr[1]) == 1:
            pi.write(int(SETTINGS["gpio"]["BIT4LED"]), 1)
        if int(arr[0]) == 1:
            pi.write(int(SETTINGS["gpio"]["BIT8LED"]), 1)
        time.sleep(2)
        pi.write(int(SETTINGS["gpio"]["BIT1LED"]), 0)
        pi.write(int(SETTINGS["gpio"]["BIT2LED"]), 0)
        pi.write(int(SETTINGS["gpio"]["BIT4LED"]), 0)
        pi.write(int(SETTINGS["gpio"]["BIT8LED"]), 0)

    def setupIO(self):
        try:

            if not pi.connected:
                exit()
            # LED setup
            pi.set_mode(int(SETTINGS["gpio"]["errorLED"]), pigpio.OUTPUT)
            pi.set_mode(int(SETTINGS["gpio"]["progressLED"]), pigpio.OUTPUT)
            # Machine setup
            pi.set_mode(int(SETTINGS["gpio"]["BIT1LED"]), pigpio.OUTPUT)
            pi.set_mode(int(SETTINGS["gpio"]["BIT2LED"]), pigpio.OUTPUT)
            pi.set_mode(int(SETTINGS["gpio"]["BIT4LED"]), pigpio.OUTPUT)
            pi.set_mode(int(SETTINGS["gpio"]["BIT8LED"]), pigpio.OUTPUT)
            pi.write(int(SETTINGS["gpio"]["BIT1LED"]), 0)
            pi.write(int(SETTINGS["gpio"]["BIT2LED"]), 0)
            pi.write(int(SETTINGS["gpio"]["BIT4LED"]), 0)
            pi.write(int(SETTINGS["gpio"]["BIT8LED"]), 0)

            # Input setup
            logging.debug("Inputs: %s %s %s" % (SETTINGS["gpio"]["errorInput"],SETTINGS["gpio"]["progressInput"],SETTINGS["gpio"]["highVehicle"]) )
            pi.set_pull_up_down(int(SETTINGS["gpio"]["errorInput"]), pigpio.PUD_UP)
            pi.set_pull_up_down(int(SETTINGS["gpio"]["progressInput"]), pigpio.PUD_DOWN)
            pi.set_pull_up_down(int(SETTINGS["gpio"]["highVehicle"]), pigpio.PUD_DOWN)

            # Machine in progress/done
            pi.callback(int(SETTINGS["gpio"]["progressInput"]), pigpio.EITHER_EDGE, self.progressStatusChanged)
            pi.callback(int(SETTINGS["gpio"]["errorInput"]), pigpio.EITHER_EDGE, self.errorStatusChanged)
            pi.callback(int(SETTINGS["gpio"]["highVehicle"]), pigpio.EITHER_EDGE, self.highVehicleStatusChanged)
            logging.debug("GPIO setup completed successfully")

        except RuntimeError as e:
            logging.error("RuntimeError during GPIO setup: %s", e)
            pi.stop()
            raise

        except Exception as e:
            logging.error("Unexpected error during GPIO setup: %s", e)
            pi.stop()
            raise

    def changeScreen(self, screenName, *args):
        logging.debug("Showing screen %s", screenName)
        self.sm.current = screenName

    @mainthread
    def progressStatusChanged(self, *args):
        if pi.read(int(SETTINGS["gpio"]["progressInput"])):
            logging.debug("Machine in progress...")
            pi.write(int(SETTINGS["gpio"]["progressLED"]), 1)
            self.changeScreen("in_progress")
        else:
            logging.debug("Machine done!")
            pi.write(int(SETTINGS["gpio"]["progressLED"]), 0)
            # show program selection screen
            self.changeScreen("program_selection")

    @mainthread
    def errorStatusChanged(self, *args):
        if pi.read(int(SETTINGS["gpio"]["errorInput"])):
            logging.debug("Error resolved!")
            # switch on error led
            pi.write(int(SETTINGS["gpio"]["errorLED"]), 0)
            # show program selection screen
            self.changeScreen("program_selection")
        else:
            logging.debug("Error detected!")
            # switch on error led
            pi.write(int(SETTINGS["gpio"]["errorLED"]), 1)
            # show error screen
            self.changeScreen("error")

    @mainthread
    def highVehicleStatusChanged(self, *args):
        if pi.read(int(SETTINGS["gpio"]["highVehicle"])):
            logging.debug("High vehicle detected!")
            self.HIGH_VEHICLE = True
            # show program selection screen for high vehicles
            self.changeScreen("program_selection_high")
        else:
            logging.debug("High vehicle no longer detected")
            self.HIGH_VEHICLE = False
            # show normal program selection screen
            self.changeScreen("program_selection")

def signal_handler(sig, frame):
    logging.debug("Cleaning up GPIO ports")
    pi.stop()
    logging.debug("Exiting....")
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    carwash = Carwash()
    carwash.run()
