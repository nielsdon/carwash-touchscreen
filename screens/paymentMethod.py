from kivy.uix.screenmanager import Screen
from kivy.app import App

class PaymentMethod(Screen):
    def selectPin(self):
        print("PIN clicked")
        app = App.get_running_app()
        app.changeScreen('payment')

    def selectWashcard(self):
        print("Washcard clicked")
        app = App.get_running_app()
        app.changeScreen('payment_washcard')

    def selectCoupon(self):
        print("Coupon clicked")
        app = App.get_running_app()
        app.changeScreen('coupon_code')
        
    def cancel(self):
        print("Cancel clicked")
        app = App.get_running_app()
        app.show_start_screen()