from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.properties import StringProperty
from kivy.core.window import Window
import logging
logging.basicConfig(level=logging.DEBUG)


class CustomButton(Button):
    button_text = StringProperty("")
    image_source = StringProperty("")


class MyLayout(BoxLayout):
    def update_label(self, text):
        self.ids.label_id.text = f"You clicked: {text}"


class MyApp(App):
    # Window.rotation = 90

    def build(self):
        return MyLayout()


if __name__ == '__main__':
    MyApp().run()
