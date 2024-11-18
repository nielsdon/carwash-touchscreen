from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock


class Finished(Screen):
    def on_enter(self, *args, **kwargs):
        # wait 10 seconds before showing the start screen again
        Clock.schedule_once(self.change_screen, 20)

    def change_screen(self, _):
        app = App.get_running_app()
        app.show_start_screen()
