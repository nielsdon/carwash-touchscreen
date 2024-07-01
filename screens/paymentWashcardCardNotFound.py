from kivy.uix.screenmanager import Screen
from kivy.app import App
import logging
import time

class PaymentWashcardCardNotFound(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== No Washcard found ===")
        app = App.get_running_app()
        time.sleep(3)
        app.show_start_screen()