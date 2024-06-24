from kivy.uix.screenmanager import Screen
from kivy.app import App
import logging
import time

class PaymentSuccess(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Payment success ===")
        app = App.get_running_app()
        app.startMachine()
        if app.TEST_MODE:
            time.sleep(3)
            app.changeScreen('program_selection')