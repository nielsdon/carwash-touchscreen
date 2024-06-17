from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.app import App
import logging

class ProgramSelection(Screen):
    def __init__(self, **kwargs):
        SETTINGS = kwargs.pop('settings', None)
        super(ProgramSelection, self).__init__(**kwargs)
        layout = self.ids.selectionLayout
        for idx, data in enumerate(SETTINGS["prices"], start=0):
            if 'WASH' in data:
                counter = idx + 1
                btn = Button(text="Wasprogramma %s" % str(counter), background_color=[0.21,0.69,0.94,1], font_size="42sp", color=[1,1,1,1])
                #print("Wasprogramma %s" % str(counter))
                btn.bind(on_release=lambda instance, counter=counter: self.selectProgram(counter))
                layout.add_widget(btn)
        btn = Button(text="Waspas opwaarderen", background_color=[0.21,0.69,0.94,1], font_size="42sp", color=[1,1,1,1])
        btn.bind(on_release=lambda instance: self.upgradeWashcard())
        layout.add_widget(btn)
        
    def on_enter(self, *args, **kwargs):
        logging.debug("=== Program selection ===")
        # You can optionally call the superclass's method if needed
        super().on_enter(*args, **kwargs)
        app = App.get_running_app()
        # Make sure the selection for high vehicles is shown when returning to program selection
        if app.HIGH_VEHICLE:
            logging.debug("High vehicle detected!")
            # show program selection screen for high vehicles
            app.changeScreen("program_selection_high")

    def selectProgram(self, program):
        app = App.get_running_app()
        app.selectProgram(program)

    def upgradeWashcard(self):
        app = App.get_running_app()
        app.changeScreen("upgrade_washcard_read_card")