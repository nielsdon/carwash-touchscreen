from kivy.uix.screenmanager import Screen
from kivy.app import App
import logging

class UpgradeWashcardChooseAmount(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Upgrade Washcard - Choose Amount ===")

    def chooseAmount(self, amount):
        logging.debug("=== Selected amount: %s", str(amount))
        app = App.get_running_app()
        app.washcardTopup = amount
        app.changeScreen("upgrade_washcard_payment")

    def cancel(self):
        app = App.get_running_app()
        app.changeScreen("program_selection")