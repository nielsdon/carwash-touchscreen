from kivy.uix.screenmanager import Screen
from kivy.app import App
import logging
import time

class PaymentWashcardCardNotValid(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Washcard not valid ===")
        app = App.get_running_app()
        time.sleep(3)
        app.changeScreen('program_selection')