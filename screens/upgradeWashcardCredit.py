from kivy.uix.screenmanager import Screen
from kivy.app import App
import logging
import time

class UpgradeWashcardCredit(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Attempt topup credit card ===")
        app = App.get_running_app()
        time.sleep(6)
        app.show_start_screen()
