from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.core.window import Window

# Import the custom keyboard class
from screens.couponkeyboard import CouponKeyboard

class CouponCode(Screen):
    def __init__(self, **kwargs):
        super(CouponCode, self).__init__(**kwargs)
        self.keyboard = None

    def on_enter(self):
        # Set focus to the text input when the screen loads
        self.ids.text_input.focus = True
        # Show the custom keyboard
        self.show_keyboard(self.ids.text_input)

    def show_keyboard(self, target):
        self.keyboard = Window.request_keyboard(self._keyboard_close, target, 'text')
        if self.keyboard.widget:
            self._vkeyboard = CouponKeyboard(target=target)
            self.keyboard.widget = self._vkeyboard

    def _keyboard_close(self):
        if self.keyboard:
            self.keyboard.release()
            self.keyboard = None