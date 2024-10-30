import logging
from kivy.uix.screenmanager import Screen
from kivy.factory import Factory
from kivy.app import App


class ProgramSelection(Screen):
    def __init__(self, **kwargs):
        settings = kwargs.pop('settings', None)
        super(ProgramSelection, self).__init__(**kwargs)
        layout = self.ids.selectionLayout
        for _, data in enumerate(settings["general"]["defaultPrograms"], start=0):
            buttonLabel = settings["names"][data]
            btn = Factory.BorderedButton(text=buttonLabel)
            btn.bind(on_release=lambda instance, program=data: self.select_program(program))
            layout.add_widget(btn)

    def on_enter(self, *args, **kwargs):
        logging.debug("=== Program selection ===")
        super().on_enter(*args, **kwargs)

    def select_program(self, program):
        app = App.get_running_app()
        app.select_program(program)
