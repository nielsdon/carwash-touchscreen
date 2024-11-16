from kivy.uix.screenmanager import Screen
from kivy.app import App
import time


class Finished(Screen):
    def on_enter(self, *args, **kwargs):
        app = App.get_running_app()
        # wait 10 seconds before showing the start screen again
        time.sleep(10)
        app.show_start_screen()
