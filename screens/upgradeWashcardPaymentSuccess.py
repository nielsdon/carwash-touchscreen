import logging
import time
from kivy.uix.screenmanager import Screen
from kivy.app import App

class UpgradeWashcardPaymentSuccess(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Upgrade washcard - payment success ===")
        app = App.get_running_app()
        card = app.activeWashcard
        card.upgrade(app.washcardTopup)
        time.sleep(5)
        app.activeWashcard = ''
        app.washcardTopup = ''
        app.show_start_screen()