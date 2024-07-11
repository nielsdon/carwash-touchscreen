import logging
import locale
import threading
from kivy.uix.screenmanager import Screen
from kivy.app import App
from washcard import Washcard

class UpgradeWashcardReadCard(Screen):
    """ Reading the card and loading the info """
    SETTINGS = {}
    washcard = None

    def __init__(self, **kwargs):
        self.SETTINGS = kwargs.pop('settings', None)
        super(UpgradeWashcardReadCard, self).__init__(**kwargs)
        self.washcard = Washcard(self.SETTINGS)

    def on_enter(self, *args, **kwargs):
        logging.debug("=== Upgrade washcard - read card ===")
        # Run the reader in a separate thread
        reading_thread = threading.Thread(target=self.washcard.readCard, args=(self.processReadResults,))
        reading_thread.start()
    
    def processReadResults(self):
        app = App.get_running_app()
        if self.washcard.uid == '':
            app.changeScreen('payment_washcard_card_not_found')
        elif self.washcard.carwash == '':
            app.changeScreen('payment_washcard_card_not_valid')
        elif self.washcard.credit == 1:
            app.changeScreen('upgrade_washcard_credit')
        elif int(self.washcard.carwash.id) != app.CARWASH_ID:
            logging.debug('Washcard carwash_id: %s', str(self.washcard.carwash.id))
            logging.debug('Config carwash_id: %s', app.CARWASH_ID)
            screen = app.sm.get_screen('payment_washcard_wrong_carwash')
            screen.ids.lbl_carwash.text = self.washcard.carwash.name + '\n' + self.washcard.carwash.city
            app.changeScreen('payment_washcard_wrong_carwash')
        else:
            screen = app.sm.get_screen('upgrade_washcard_choose_amount')
            screen.ids.lbl_balance.text = locale.currency(
                float(self.washcard.balance))
            screen.ids.lbl_carwash.text = self.washcard.carwash.name + ' - ' + self.washcard.carwash.city
            screen.ids.lbl_company.text = self.washcard.company.name + ' - ' + self.washcard.carwash.city
            app.activeWashcard = self.washcard
            app.changeScreen('upgrade_washcard_choose_amount')

    def cancel(self):
        logging.debug("Cancelling payment with washcard...")
        self.washcard.stopReading()
        app = App.get_running_app()
        app.show_start_screen()