from kivy.uix.screenmanager import Screen
from kivy.app import App

class PaymentMethod(Screen):
    def selectPin(self):
        app = App.get_running_app()
        app.changeScreen('payment')

    def selectWashcard(self):
        app = App.get_running_app()
        app.changeScreen('payment_washcard')

    def cancel(self):
        app = App.get_running_app()
        app.show_start_screen()