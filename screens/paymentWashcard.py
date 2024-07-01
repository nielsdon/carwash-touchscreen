from kivy.uix.screenmanager import Screen
from kivy.app import App
from washcard import Washcard
import logging
import locale

class PaymentWashcard(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Payment with washcard ===")
        app = App.get_running_app()
        washcard = Washcard(app.SETTINGS)
        washcard.readCard()
        # check if we need to apply a discount
        if washcard.credit and "creditcardDiscountPercentage" in app.SETTINGS["general"]:
            logging.debug("Discount:%s",str(app.SETTINGS["general"]["creditcardDiscountPercentage"]))
            multiplier = (100 - app.SETTINGS["general"]["creditcardDiscountPercentage"]) / 100
            logging.debug("Old price:%s", str(app.activeOrder.amount))
            app.activeOrder.amount = app.activeOrder.amount * multiplier
            logging.debug("New price:%s", str(app.activeOrder.amount))
        if washcard.uid == '':
            app.changeScreen('payment_washcard_card_not_found')
        elif washcard.carwash == '':
            app.changeScreen('payment_washcard_card_not_valid')
        elif int(washcard.carwash.id) != app.CARWASH_ID:
            logging.debug("Washcard carwash_id: %s", str(washcard.carwash.id))
            logging.debug("Config carwash_id: %s", str(app.CARWASH_ID))
            screen = app.sm.get_screen('payment_washcard_wrong_carwash')
            screen.ids.lbl_carwash.text = washcard.carwash.name + '\n' + washcard.carwash.city
            app.changeScreen('payment_washcard_wrong_carwash')
        else:
            #checks done: create transaction
            response = washcard.pay(app.activeOrder)
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
                screen.ids.lbl_balance.text = locale.currency(float(washcard.balance))
                app.changeScreen('payment_washcard_insufficient_balance')
            elif response["statusCode"] == 460:
                app.changeScreen('payment_washcard_card_not_valid')
            else:
                app.changeScreen('payment_failed')
