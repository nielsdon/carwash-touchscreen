import logging
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.app import App


class ProgramSelectionHigh(Screen):
    """ The handler for the program selection screen for high vehicles """

    def __init__(self, **kwargs):
        settings = kwargs.pop('settings', None)
        super(ProgramSelectionHigh, self).__init__(**kwargs)
        layout = self.ids.selectionLayout
        textColor = [1, 1, 1, 1]
        backgroundColor = [0, 0, 0, 1]
        if "buttonBackgroundColor" in settings["general"]:
            backgroundColor = settings["general"]["buttonBackgroundColor"]
        if "buttonTextColor" in settings["general"]:
            textColor = settings["general"]["buttonTextColor"]

        for idx, data in enumerate(settings["general"]["highSensorPrograms"], start=0):
            buttonLabel = settings["names"][data]
            btn = Button(text=buttonLabel, background_color=backgroundColor,
                         background_normal='', font_size="42sp", color=textColor)
            btn.bind(on_release=lambda instance, program=data: self.select_program(program))
            layout.add_widget(btn)

    def on_enter(self, *args, **kwargs):
        logging.debug("=== Program selection for high vehicles ===")
        super().on_enter(*args, **kwargs)

    def select_program(self, program):
        """ method that is called when a selection button is tapped """
        app = App.get_running_app()
        app.select_program(program)

    def upgrade_washcard(self):
        """ method that is called when the topup button is tapped """
        app = App.get_running_app()
        app.change_screen("upgrade_washcard_read_card")
