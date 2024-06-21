from kivy.uix.screenmanager import Screen
from kivy.app import App
import logging

class ProgramSelectionHigh(Screen):
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Program selection for high vehicles ===")
        super().on_enter(*args, **kwargs)

    def selectProgram(self, program):
        app = App.get_running_app()
        app.selectProgram(program)

    def upgradeWashcard(self):
        app = App.get_running_app()
        app.changeScreen("upgrade_washcard_read_card")