import logging
import time
import threading
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.app import App
from payNL import PayNL
from washcard import Washcard

class UpgradeWashcardPayment(Screen):
    transaction_status = ''
    pay = {}
    transaction_id = 0
    cancel_transaction = threading.Event()
    settings = {}
    
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Upgrade washcard - payment ===")
        app = App.get_running_app()
        logging.debug(app.activeWashcard.uid)
        logging.debug(str(app.washcardTopup))
        self.settings = app.SETTINGS
        # pay.nl communicatie: start transaction
        self.pay = PayNL(self.settings["paynl"])
        self.transaction_id = self.pay.pay_card_upgrade(
            app.washcardTopup, app.activeWashcard)
        logging.debug("transaction_id: %s", self.transaction_id)

        # start pending requesting the transaction status with pay.nl
        self.transaction_status = 'PENDING'
        self.cancel_transaction.clear()  # Clear the stop event
        t = threading.Thread(target=self.loop)
        t.start()

    def loop(self):
        """ waiting for the transaction to finish while polling for a status every 2 sec """
        wait = 0
        app = App.get_running_app()
        while self.transaction_status == 'PENDING' and wait < 400 and self.transaction_id and not self.cancel_transaction.is_set():
            time.sleep(0.1)
            wait += 1
            if wait % 20 == 0:
                # pay.nl communicatie: check order status every 2 sec (20 * 0.1)
                self.transaction_status = self.pay.get_transaction_status(self.transaction_id)
                logging.debug("transaction_status: %s", self.transaction_status)
        # timeout is reached, status is no longer PENDING or payment is cancelled
        if self.transaction_status == 'PAID':
            logging.debug('betaling gelukt!')
            app.change_screen('upgrade_washcard_payment_success')
        elif self.cancel_transaction.is_set():
            logging.debug('transaction cancelled')
            self.cancel_transaction.clear()
            self.pay.cancel_transaction(self.transaction_id)
            app.show_start_screen()
        else:
            logging.debug('some payment error')
            #self.pay.cancelTransaction(self.transaction_id)
            Clock.schedule_once(lambda dt: app.change_screen('upgrade_washcard_payment_failed'))

    def cancel(self, *args, **kwargs):
        """ cancel button is pressed """
        logging.debug("=== Cancelling PIN payment ===")
        self.cancel_transaction.set()  # Set the stop event to true