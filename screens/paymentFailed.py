import logging
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.app import App
from functools import partial


class PaymentFailed(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Payment failed ===")
        app = App.get_running_app()
        app.activeOrder = ''
        Clock.schedule_once(partial(app.show_start_screen), 5)
