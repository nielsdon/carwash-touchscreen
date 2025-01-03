from kivy.uix.screenmanager import Screen
from kivy.app import App


class PaymentMethod(Screen):
    def selectPin(self):
        # print("PIN clicked")
        app = App.get_running_app()
        app.change_screen('payment')

    def selectWashcard(self):
        # print("Washcard clicked")
        app = App.get_running_app()
        app.change_screen('payment_washcard')

    def cancel(self):
        # print("Cancel clicked")
        app = App.get_running_app()
        app.show_start_screen()
