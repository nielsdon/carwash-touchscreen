from kivy.uix.screenmanager import Screen
from kivy.app import App
import logging
import time

class PaymentWashcardWrongCarwash(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Wrong Carwash ===")
        app = App.get_running_app()
        time.sleep(6)
        app.changeScreen('program_selection')