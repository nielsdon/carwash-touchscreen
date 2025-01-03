from kivy.uix.screenmanager import Screen
from kivy.app import App
import logging


class UpgradeWashcardChooseAmount(Screen):
    def on_enter(self, *_, **__):
        logging.debug("=== Upgrade Washcard - Choose Amount ===")

    def chooseAmount(self, amount):
        logging.debug("=== Selected amount: %s", str(amount))
        app = App.get_running_app()
        app.washcard_topup(amount)
        app.change_screen("upgrade_washcard_payment")

    def cancel(self):
        app = App.get_running_app()
        app.change_screen("program_selection")
