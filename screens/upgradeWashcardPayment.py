from kivy.uix.screenmanager import Screen
from kivy.app import App
from payNL import PayNL
import logging
import time

class UpgradeWashcardPayment(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Upgrade washcard - payment ===")
        app = App.get_running_app()
        logging.debug(app.activeWashcard.uid)
        logging.debug(str(app.washcardTopup))

        # pay.nl communicatie: start transaction
        pay = PayNL(app.SETTINGS)
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
