import logging
import time
import threading
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.app import App
from payNL import PayNL
from washcard import Washcard


class Payment(Screen):
    transaction_status = ''
    pay = False
    transaction_id = 0
    cancel_transaction = threading.Event()
    settings = {}

    def on_enter(self, *args, **kwargs):
        logging.debug("=== Payment ===")
        app = App.get_running_app()
        self.settings = app.SETTINGS
        # pay.nl communicatie: start transaction
        self.pay = PayNL(self.settings["paynl"])
        self.transaction_id = self.pay.payOrder(app.activeOrder)
        logging.debug("transaction_id: %s", self.transaction_id)

        # start pending requesting the transaction status with pay.nl
        self.transaction_status = 'PENDING'
        self.cancel_transaction.clear()  # Clear the stop event
        t = threading.Thread(target=self.loop)
        t.start()

    def loop(self):
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
            # log the transaction
            washcard = Washcard(self.settings)
            response = washcard.pay(app.activeOrder)
            logging.debug(response)
            app.change_screen('payment_success')
        elif self.cancel_transaction.is_set():
            logging.debug('transaction cancelled')
            self.cancel_transaction.clear()
            self.pay.cancel_transaction()
            app.show_start_screen()
        else:
            logging.debug('some payment error')
            # self.pay.cancelTransaction(self.transaction_id)
            Clock.schedule_once(lambda dt: app.change_screen('payment_failed'))

    def cancel(self, *args, **kwargs):
        logging.debug("=== Cancelling PIN payment ===")
        self.cancel_transaction.set()  # Set the stop event to true
