from kivy.uix.screenmanager import Screen
from kivy.app import App


class MoveVehicle(Screen):

    def upgrade_washcard(self):
        app = App.get_running_app()
        app.change_screen("upgrade_washcard_read_card")
