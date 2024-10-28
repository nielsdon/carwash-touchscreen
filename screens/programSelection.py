import logging
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.factory import Factory
from kivy.app import App

class ProgramSelection(Screen):
    def __init__(self, **kwargs):
        SETTINGS = kwargs.pop('settings', None)
        super(ProgramSelection, self).__init__(**kwargs)
        layout = self.ids.selectionLayout
        for idx, data in enumerate(SETTINGS["general"]["defaultPrograms"], start=0):
            buttonLabel = SETTINGS["names"][data]
            btn = Factory.BorderedButton(text=buttonLabel)
            btn.bind(on_release=lambda instance, program=data: self.selectProgram(program))
            layout.add_widget(btn)
        
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Program selection ===")
        super().on_enter(*args, **kwargs)

    def selectProgram(self, program):
        app = App.get_running_app()
        app.selectProgram(program)
