"""The Main application for the touchscreen"""
import configparser
import locale
import logging
import os
import signal
import sys
import time
from functools import partial

import RPi.GPIO as GPIO
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager

from payNL import PayNL
from washcard import Washcard
from washingOrder import Order

os.environ['KIVY_NO_FILELOG'] = '1'  # eliminate file log
# globals
CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
CARWASH_ID = int(CONFIG.get('Washcard', 'carwashId'))
ERROR_INPUT = int(CONFIG.get('GPIO', 'errorInput'))
PROGRESS_INPUT = int(CONFIG.get('GPIO', 'progressInput'))
PROGRESS_LED = int(CONFIG.get('GPIO', 'progressLED'))
ERROR_LED = int(CONFIG.get('GPIO', 'errorLED'))
HIGH_VEHICLE_INPUT = int(CONFIG.get('GPIO', 'highVehicle'))
BIT1LED = int(CONFIG.get('GPIO', 'BIT1LED'))
BIT2LED = int(CONFIG.get('GPIO', 'BIT2LED'))
BIT4LED = int(CONFIG.get('GPIO', 'BIT4LED'))
BIT8LED = int(CONFIG.get('GPIO', 'BIT8LED'))
Logger.setLevel(int(CONFIG.get('General', 'logLevel')))
logging.basicConfig(
    encoding='utf-8', level=int(CONFIG.get('General', 'logLevel')))
locale.setlocale(locale.LC_ALL, '')


class ProgramSelection(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Program selection ===")
        # You can optionally call the superclass's method if needed
        super().on_enter(*args, **kwargs)

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


class PaymentWashcard(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Payment with washcard ===")
        app = App.get_running_app()
        washcard = Washcard()
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
            responseCode = washcard.pay(app.activeOrder)
            logging.debug('Response code: %s', str(responseCode))
            if responseCode == 0:
                app.changeScreen('payment_success')
            elif responseCode == 1:
                app.changeScreen('payment_washcard_insufficient_balance')
            elif responseCode == 2:
                app.changeScreen('payment_washcard_card_not_found')
            elif responseCode == 3:
                app.changeScreen('payment_washcard_card_not_valid')
            else:
                app.changeScreen('payment_failed')


class Payment(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Payment ===")
        app = App.get_running_app()

        # pay.nl communicatie: start transaction
        pay = PayNL()
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
        washcard = Washcard()
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
        pay = PayNL()
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

    def build(self):
        Window.rotation = 90  # Rotate the window 90 degrees
        # setup the screens
        Builder.load_file('screens.kv')

        # setup possible uptick based on weekday
        # self.setUptick()

        # setup screens
        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(ProgramSelection(name="program_selection"))
        self.sm.add_widget(ProgramSelectionHigh(name="program_selection_high"))
        self.sm.add_widget(PaymentMethod(name="payment_method"))
        self.sm.add_widget(Payment(name="payment"))
        self.sm.add_widget(PaymentWashcard(name="payment_washcard"))
        self.sm.add_widget(PaymentWashcardCardNotValid(
            name="payment_washcard_card_not_valid"))
        self.sm.add_widget(PaymentWashcardWrongCarwash(
            name="payment_washcard_wrong_carwash"))
        self.sm.add_widget(PaymentWashcardCardNotFound(
            name="payment_washcard_card_not_found"))
        self.sm.add_widget(PaymentWashcardInsufficientBalance(
            name="payment_washcard_insufficient_balance"))
        self.sm.add_widget(PaymentFailed(name="payment_failed"))
        self.sm.add_widget(PaymentSuccess(name="payment_success"))
        self.sm.add_widget(UpgradeWashcardReadCard(
            name="upgrade_washcard_read_card"))
        self.sm.add_widget(UpgradeWashcardChooseAmount(
            name="upgrade_washcard_choose_amount"))
        self.sm.add_widget(UpgradeWashcardPayment(
            name="upgrade_washcard_payment"))
        self.sm.add_widget(UpgradeWashcardPaymentSuccess(
            name="upgrade_washcard_payment_success"))
        self.sm.add_widget(UpgradeWashcardPaymentFailed(
            name="upgrade_washcard_payment_failed"))
        self.sm.add_widget(Error(name="error"))
        self.sm.add_widget(InProgress(name="in_progress"))
        # setup leds
        self.setupIO()
        return self.sm

    def selectProgram(self, program):
        logging.debug("Program selected: %s", str(program))
        order = Order(program)
        self.activeOrder = order
        self.changeScreen("payment_method")

    def startMachine(self):
        bin = '{0:04b}'.format(self.activeOrder.program)
        logging.debug("Starting machine. Binary: %s", str(bin))
        arr = list(bin)
        print(arr)
        if int(arr[3]) == 1:
            GPIO.output(BIT1LED, GPIO.HIGH)
        if int(arr[2]) == 1:
            GPIO.output(BIT2LED, GPIO.HIGH)
        if int(arr[1]) == 1:
            GPIO.output(BIT4LED, GPIO.HIGH)
        if int(arr[0]) == 1:
            GPIO.output(BIT8LED, GPIO.HIGH)
        time.sleep(2)
        GPIO.output(BIT1LED, GPIO.LOW)
        GPIO.output(BIT2LED, GPIO.LOW)
        GPIO.output(BIT4LED, GPIO.LOW)
        GPIO.output(BIT8LED, GPIO.LOW)

    def setupIO(self):
        try:
            GPIO.setmode(GPIO.BCM)
            # LED setup
            GPIO.setup(ERROR_LED, GPIO.OUT)
            GPIO.setup(PROGRESS_LED, GPIO.OUT)
            # Machine setup
            GPIO.setup(BIT1LED, GPIO.OUT)
            GPIO.setup(BIT2LED, GPIO.OUT)
            GPIO.setup(BIT4LED, GPIO.OUT)
            GPIO.setup(BIT8LED, GPIO.OUT)
            GPIO.output(BIT1LED, GPIO.LOW)
            GPIO.output(BIT2LED, GPIO.LOW)
            GPIO.output(BIT4LED, GPIO.LOW)
            GPIO.output(BIT8LED, GPIO.LOW)

            # Input setup
            GPIO.setup(ERROR_INPUT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(PROGRESS_INPUT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(HIGH_VEHICLE_INPUT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

            logging.debug(str(ERROR_INPUT))
            logging.debug(str(PROGRESS_INPUT))
            logging.debug(str(HIGH_VEHICLE_INPUT))
            # Machine in progress/done
            #GPIO.add_event_detect(PROGRESS_INPUT, GPIO.BOTH, callback=self.progressStatusChanged, bouncetime=300)
            # Error detected/resolved
            #GPIO.add_event_detect(ERROR_INPUT, GPIO.BOTH, callback=self.errorStatusChanged, bouncetime=300)
            # High vehicle status changed
            #GPIO.add_event_detect(HIGH_VEHICLE_INPUT, GPIO.BOTH, callback=self.highVehicleStatusChanged, bouncetime=300)
            logging.debug("GPIO setup completed successfully")

        except RuntimeError as e:
            logging.error("RuntimeError during GPIO setup: %s", e)
            GPIO.cleanup()  # Ensure GPIO is cleaned up to reset the state
            raise

        except Exception as e:
            logging.error("Unexpected error during GPIO setup: %s", e)
            GPIO.cleanup()  # Ensure GPIO is cleaned up to reset the state
            raise

    def changeScreen(self, screenName, *args):
        logging.debug("Showing screen %s", screenName)
        self.sm.current = screenName

    @mainthread
    def progressStatusChanged(self, *args):
        if GPIO.input(PROGRESS_INPUT):
            logging.debug("Machine in progress...")
            GPIO.output(PROGRESS_LED, GPIO.HIGH)
            self.changeScreen("in_progress")
        else:
            logging.debug("Machine done!")
            GPIO.output(PROGRESS_LED, GPIO.LOW)
            # show program selection screen
            self.changeScreen("program_selection")

    @mainthread
    def errorStatusChanged(self, *args):
        if GPIO.input(ERROR_INPUT):
            logging.debug("Error resolved!")
            # switch on error led
            GPIO.output(ERROR_LED, GPIO.LOW)
            # show program selection screen
            self.changeScreen("program_selection")
        else:
            logging.debug("Error detected!")
            # switch on error led
            GPIO.output(ERROR_LED, GPIO.HIGH)
            # show error screen
            self.changeScreen("error")

    @mainthread
    def highVehicleStatusChanged(self, *args):
        if GPIO.input(HIGH_VEHICLE_INPUT):
            logging.debug("High vehicle detected!")
            # show program selection screen for high vehicles
            self.changeScreen("program_selection_high")
        else:
            logging.debug("High vehicle removed")
            # show normal program selection screen
            self.changeScreen("program_selection")

def signal_handler(sig, frame):
    logging.debug("Cleaning up GPIO ports")
    GPIO.cleanup()
    logging.debug("Exiting....")
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    carwash = Carwash()
    carwash.run()
