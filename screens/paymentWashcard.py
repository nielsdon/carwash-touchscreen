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
        self.reading_thread = threading.Thread(target=self.washcard.read_card, args=(self.processReadResults,), name="read_card")
        self.reading_thread.start()

    def processReadResults(self):
        """Process results after attempting to read NFC card."""
        self.thread_running = False  # Reset the flag when done
        app = App.get_running_app()
        logging.debug("Processing card read results....")
        logging.debug("Card UID: %s", self.washcard.uid)

        # Step 1: Validate the card
        if not self.validate_card():
            return

        # Step 2: Apply discount if applicable
        self.apply_discount()

        # Step 3: Process payment and handle the response
        response = self.washcard.pay(app.activeOrder)
        self.handle_payment_response(response)

    def validate_card(self):
        """Validates the presence, validity, and carwash association of the card."""
        app = App.get_running_app()

        # Check if UID is missing or card data not loaded
        if not self.washcard.uid:
            app.change_screen('payment_washcard_card_not_found')
            return False

        if not self.washcard.carwash:
            app.change_screen('payment_washcard_card_not_valid')
            return False

        # Check if the card belongs to the correct carwash
        if int(self.washcard.carwash.id) != app.carwash_id:
            logging.debug("Washcard carwash_id: %s", str(self.washcard.carwash.id))
            logging.debug("Config carwash_id: %s", str(app.carwash_id))
            screen = app.sm.get_screen('payment_washcard_wrong_carwash')
            screen.ids.lbl_carwash.text = f"{self.washcard.carwash.name}\n{self.washcard.carwash.city}"
            app.change_screen('payment_washcard_wrong_carwash')
            return False

        return True

    def apply_discount(self):
        """Applies discount to the active order if eligible."""
        app = App.get_running_app()

        if self.washcard.credit and "creditcardDiscountPercentage" in app.SETTINGS["general"]:
            discount_percentage = app.SETTINGS["general"]["creditcardDiscountPercentage"]
            logging.debug("Applying discount of %s%%", discount_percentage)
            multiplier = (100 - discount_percentage) / 100
            logging.debug("Old price: %s", app.activeOrder.amount)
            app.activeOrder.amount *= multiplier
            logging.debug("New price: %s", app.activeOrder.amount)

    def handle_payment_response(self, response):
        """Handles the payment response and displays the appropriate screen."""
        app = App.get_running_app()

        if response["statusCode"] == 200:
            screen = app.sm.get_screen('payment_success')
            if 'balance' in response:
                logging.debug('New balance: %s %s', locale.LC_MONETARY, locale.currency(float(response["balance"])))
                screen.ids.lbl_balance_text.text = "Nieuw saldo:"
                screen.ids.lbl_balance.text = locale.currency(float(response["balance"]))
            app.change_screen('payment_success')
        elif response["statusCode"] == 462:
            screen = app.sm.get_screen('payment_washcard_insufficient_balance')
            screen.ids.lbl_balance.text = locale.currency(float(self.washcard.balance))
            app.change_screen('payment_washcard_insufficient_balance')
        elif response["statusCode"] == 460:
            app.change_screen('payment_washcard_card_not_valid')
        else:
            app.change_screen('payment_failed')

    def cancel(self):
        logging.debug("Cancelling payment with washcard...")
        self.washcard.stop_reading()
        if self.reading_thread and self.reading_thread.is_alive():
            self.reading_thread.join(timeout=1)  # Wait for the thread to finish with a timeout
            if self.reading_thread.is_alive():
                logging.error("Failed to terminate reading thread")
                return  # Exit without setting thread_running to False
        self.thread_running = False  # Reset the flag on successful termination
        app = App.get_running_app()
        app.show_start_screen()
