from kivy.uix.screenmanager import Screen
from kivy.app import App
#import logging
import time

class UpgradeWashcardPaymentFailed(Screen):
    def on_enter(self, *args, **kwargs):
#        logging.debug("=== Upgrade washcard - payment failed ===")
        app = App.get_running_app()
        app.activeWashcard = ''
        app.washcardTopup = ''
        time.sleep(5)
        app.show_start_screen()