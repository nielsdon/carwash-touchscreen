import logging
import locale
import threading
from kivy.uix.screenmanager import Screen
from kivy.app import App
from washcard import Washcard

class PaymentWashcard(Screen):
    reading_thread = None
    thread_running = False
    
    def __init__(self, **kwargs):
        super(PaymentWashcard, self).__init__(**kwargs)
        self.washcard = None
        self.reading_event = threading.Event()

    def on_enter(self, *args, **kwargs):
        logging.debug("=== Payment with washcard ===")
        if self.thread_running:
            logging.debug("Reading thread is already running")
            return

        app = App.get_running_app()
        self.washcard = Washcard(app.SETTINGS)
        self.thread_running = True
        self.washcard.stop_event.clear()  # Clear the stop event before starting the thread
        # Run the reader in a separate thread
        self.reading_thread = threading.Thread(target=self.washcard.readCard, args=(self.processReadResults,), name="readCard")
        self.reading_thread.start()
        
    def processReadResults(self):
        self.thread_running = False  # Reset the flag when done
        app = App.get_running_app()
        # check if we need to apply a discount
        logging.debug("Processing card read results....")
        logging.debug("Card UID: %s", self.washcard.uid)
        if self.washcard.credit and "creditcardDiscountPercentage" in app.SETTINGS["general"]:
            logging.debug("Discount:%s",str(app.SETTINGS["general"]["creditcardDiscountPercentage"]))
            multiplier = (100 - app.SETTINGS["general"]["creditcardDiscountPercentage"]) / 100
            logging.debug("Old price:%s", str(app.activeOrder.amount))
            app.activeOrder.amount = app.activeOrder.amount * multiplier
            logging.debug("New price:%s", str(app.activeOrder.amount))
        if self.washcard.uid == '':
            app.changeScreen('payment_washcard_card_not_found')
        elif self.washcard.carwash == '':
            app.changeScreen('payment_washcard_card_not_valid')
        elif int(self.washcard.carwash.id) != app.carwash_id:
            logging.debug("Washcard carwash_id: %s", str(self.washcard.carwash.id))
            logging.debug("Config carwash_id: %s", str(app.carwash_id))
            screen = app.sm.get_screen('payment_washcard_wrong_carwash')
            screen.ids.lbl_carwash.text = self.washcard.carwash.name + '\n' + self.washcard.carwash.city
            app.changeScreen('payment_washcard_wrong_carwash')
        else:
            #checks done: create transaction
            response = self.washcard.pay(app.activeOrder)
            #logging.debug('Response status code: %s', str(response["statusCode"]))
            logging.debug('Response:')
            logging.debug(response)
            if response["statusCode"] == 200:
                screen = app.sm.get_screen('payment_success')
                if 'balance' in response:
                    logging.debug('New balance: %s %s',  locale.LC_MONETARY, locale.currency(float(response["balance"])))
                    screen.ids.lbl_balance_text.text = "Nieuw saldo:"
                    screen.ids.lbl_balance.text = locale.currency(float(response["balance"]))
                app.changeScreen('payment_success')
            elif response["statusCode"] == 462:
                screen = app.sm.get_screen('payment_washcard_insufficient_balance')
                screen.ids.lbl_balance.text = locale.currency(float(self.washcard.balance))
                app.changeScreen('payment_washcard_insufficient_balance')
            elif response["statusCode"] == 460:
                app.changeScreen('payment_washcard_card_not_valid')
            else:
                app.changeScreen('payment_failed')

    def cancel(self):
        logging.debug("Cancelling payment with washcard...")
        self.washcard.stopReading()
        if self.reading_thread and self.reading_thread.is_alive():
            self.reading_thread.join(timeout=1)  # Wait for the thread to finish with a timeout
            if self.reading_thread.is_alive():
                logging.error("Failed to terminate reading thread")
                return  # Exit without setting thread_running to False
        self.thread_running = False  # Reset the flag on successful termination
        app = App.get_running_app()
        app.show_start_screen()