from carwash import Carwash  # Adjust this to your main app class
import pytest
from kivy.config import Config
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'fullscreen', '0')


@pytest.fixture
def carwash_app():
    app = Carwash()
    app.run()
    yield app
    app.stop()


def test_screen_initialization(carwash_app):
    assert carwash_app.sm.current == "initial_screen_name"  # Replace with actual screen name


def test_sample_widget_interaction(carwash_app):
    button = carwash_app.root.ids['your_button_id']  # Replace with actual widget ID
    button.trigger_action()  # Simulate button click
    assert carwash_app.some_state == "expected_state"  # Replace with expected state
