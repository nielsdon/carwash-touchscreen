from kivy.uix.screenmanager import Screen
from kivy.app import App
import logging
import time

class PaymentWashcardInsufficientBalance(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Insufficient balance on washcard ===")
        app = App.get_running_app()
        time.sleep(3)
        app.changeScreen('program_selection')