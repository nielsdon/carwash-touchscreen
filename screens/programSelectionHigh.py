from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.app import App
import logging

class ProgramSelectionHigh(Screen):
    def __init__(self, **kwargs):
        SETTINGS = kwargs.pop('settings', None)
        super(ProgramSelectionHigh, self).__init__(**kwargs)
        layout = self.ids.selectionLayout
        textColor = [1,1,1,1]
        backgroundColor = [0,0,0,1]
        if "buttonBackgroundColor" in SETTINGS["general"]:
            backgroundColor = SETTINGS["general"]["buttonBackgroundColor"]
        if "buttonTextColor" in SETTINGS["general"]:
            textColor = SETTINGS["general"]["buttonTextColor"]
        
        for idx, data in enumerate(SETTINGS["general"]["highSensorPrograms"], start=0):
            buttonLabel = SETTINGS["names"][data]
            btn = Button(text=buttonLabel, background_color=backgroundColor, background_normal='', font_size="42sp", color=textColor)
            btn.bind(on_release=lambda instance, program=data: self.selectProgram(program))
            layout.add_widget(btn)

    def on_enter(self, *args, **kwargs):
        logging.debug("=== Program selection for high vehicles ===")
        super().on_enter(*args, **kwargs)

    def selectProgram(self, program):
        app = App.get_running_app()
        app.selectProgram(program)

    def upgradeWashcard(self):
        app = App.get_running_app()
        app.changeScreen("upgrade_washcard_read_card")
