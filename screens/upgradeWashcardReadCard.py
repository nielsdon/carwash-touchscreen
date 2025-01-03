import logging
import locale
import threading
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
from washcard import Washcard


class UpgradeWashcardReadCard(Screen):
    """ Reading the card and loading the info """
    SETTINGS = {}
    washcard = None
    reading_thread = None
    thread_running = False

    def __init__(self, **kwargs):
        self.SETTINGS = kwargs.pop('settings', None)
        super(UpgradeWashcardReadCard, self).__init__(**kwargs)
        self.washcard = Washcard(self.SETTINGS)
        self.timeout_event = None  # Will store the timeout event

    def on_enter(self, *args, **kwargs):
        logging.debug("=== Upgrade washcard - read card ===")

        # if no card is read within 10 seconds, go back to start screen
        self.timeout_event = Clock.schedule_once(self.cancel, 10)

        if self.thread_running:
            logging.debug("Reading thread is already running")
            return

        self.thread_running = True
        self.washcard.stop_event.clear()  # Clear the stop event before starting the thread
        # Run the reader in a separate thread
        self.reading_thread = threading.Thread(target=self.washcard.read_card, args=(self.processReadResults,), name="read_card")
        self.reading_thread.start()
        self.list_running_threads()

    # Function to list all running threads
    def list_running_threads(self):
        for thread in threading.enumerate():
            logging.debug(f"Thread Name: {thread.name}, Thread ID: {thread.ident}")

    def processReadResults(self):
        self.thread_running = False  # Reset the flag when done
        # remove the read timeout
        Clock.unschedule(self.timeout_event)  # Cancel the timeout if card is read

        app = App.get_running_app()
        if self.washcard.uid == '':
            app.change_screen('payment_washcard_card_not_found')
        elif self.washcard.carwash == '':
            app.change_screen('payment_washcard_card_not_valid')
        elif self.washcard.credit == 1:
            app.change_screen('upgrade_washcard_credit')
        elif int(self.washcard.carwash.id) != app.carwash_id:
            logging.debug('Washcard carwash_id: %s', str(self.washcard.carwash.id))
            logging.debug('Config carwash_id: %s', app.carwash_id)
            screen = app.sm.get_screen('payment_washcard_wrong_carwash')
            screen.ids.lbl_carwash.text = self.washcard.carwash.name + '\n' + self.washcard.carwash.city
            app.change_screen('payment_washcard_wrong_carwash')
        else:
            screen = app.sm.get_screen('upgrade_washcard_choose_amount')
            screen.ids.lbl_balance.text = locale.currency(
                float(self.washcard.balance))
            app.activeWashcard = self.washcard
            app.change_screen('upgrade_washcard_choose_amount')

    def cancel(self, dt=None):
        logging.debug("Cancelling upgrading washcard...")
        # remove the read timeout
        Clock.unschedule(self.timeout_event)  # Cancel the timeout if card is read
        self.washcard.stop_reading()
        if self.reading_thread and self.reading_thread.is_alive():
            self.reading_thread.join(timeout=1)  # Wait for the thread to finish with a timeout
            if self.reading_thread.is_alive():
                logging.error("Failed to terminate reading thread")
                return  # Exit without setting thread_running to False
        self.thread_running = False  # Reset the flag on successful termination
        app = App.get_running_app()
        app.show_start_screen()
