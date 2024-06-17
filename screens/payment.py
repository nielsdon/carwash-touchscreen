from kivy.uix.screenmanager import Screen
from kivy.app import App
from payNL import PayNL
from washcard import Washcard
import logging
import time

class Payment(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Payment ===")
        app = App.get_running_app()
        SETTINGS = app.SETTINGS;
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
            # log the transaction
            washcard = Washcard(SETTINGS)
            response = washcard.pay(app.activeOrder)
            logging.debug(response)
            app.changeScreen('payment_success')
        else:
            logging.debug('fout bij betaling')
            pay.cancelTransaction(transactionId)
            app.changeScreen('payment_failed')
