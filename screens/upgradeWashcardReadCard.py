import logging
import locale
from kivy.uix.screenmanager import Screen
from kivy.app import App
from washcard import Washcard

class UpgradeWashcardReadCard(Screen):
    """ Reading the card and loading the info """
    SETTINGS = {}

    def __init__(self, **kwargs):
        self.SETTINGS = kwargs.pop('settings', None)
        super(UpgradeWashcardReadCard, self).__init__(**kwargs)

    def on_enter(self, *args, **kwargs):
        logging.debug("=== Upgrade washcard - read card ===")
        app = App.get_running_app()
        washcard = Washcard(self.SETTINGS)
        washcard.readCard()
        if washcard.uid == '':
            app.changeScreen('payment_washcard_card_not_found')
        elif washcard.carwash == '':
            app.changeScreen('payment_washcard_card_not_valid')
        elif washcard.credit == 1:
            app.changeScreen('upgrade_washcard_credit')
        elif int(washcard.carwash.id) != app.CARWASH_ID:
            logging.debug('Washcard carwash_id: %s', str(washcard.carwash.id))
            logging.debug('Config carwash_id: %s', app.CARWASH_ID)
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
