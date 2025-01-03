import unittest
from unittest.mock import patch, MagicMock
# import sys

# Mock pigpio before importing carwash
# Mock Kivy components before importing carwash
mock_kivy_modules = {
    'kivy': MagicMock(),
    'kivy.app': MagicMock(),
    'kivy.uix.screenmanager': MagicMock(),
    'kivy.uix.relativelayout': MagicMock(),
    'kivy.uix.floatlayout': MagicMock(),
    'kivy.uix.layout': MagicMock(),
    'kivy.uix.widget': MagicMock(),
    'kivy.lang': MagicMock(),
    'kivy.clock': MagicMock(),
    'kivy.core': MagicMock(),
    'kivy.logger': MagicMock(),
    'kivy.core.window': MagicMock(),  # Specifically mock kivy.core.window
}

with patch.dict('sys.modules', mock_kivy_modules):
    from carwash import Carwash


class TestCarwash(unittest.TestCase):

    @patch('carwash.pigpio.pi')
    def test_setup(self, mock_pi):
        # Create a mock instance of pigpio.pi
        mock_instance = mock_pi.return_value

        # Define mock settings for GPIO
        mock_settings = {
            "general": {
                "logLevel": 10,
                "nfcReader": "/dev/input/event1",
                "nfcReaderVendorIdDeviceId": "09d8:0410",
                "mannedDays": [
                    {
                        "weekday": 3,
                        "start": "09:00",
                        "end": "17:00"
                    },
                    {
                        "weekday": 4,
                        "start": "09:00",
                        "end": "17:00"
                    },
                    {
                        "weekday": 5,
                        "start": "09:00",
                        "end": "17:00"
                    }
                ],
                "mannedUptick": 2,
                "buttonBackgroundColor": [
                    0,
                    0.569,
                    0.867,
                    1
                ],
                "buttonTextColor": [
                    1,
                    1,
                    1,
                    1
                ],
                "backgroundColor": [
                    1,
                    1,
                    1,
                    1
                ],
                "textColor": [
                    0,
                    0,
                    0,
                    1
                ],
                "defaultPrograms": [
                    "WASH_1",
                    "WASH_2",
                    "WASH_3"
                ],
                "highSensorPrograms": [
                    "WASH_4",
                    "WASH_5",
                    "WASH_6"
                ],
                "supportPhone": "06 517 249 73",
                "creditcardDiscountPercentage": 0
            },
            "names": {
                "WASH_1": "Wasprogramma 1",
                "WASH_2": "Wasprogramma 2",
                "WASH_3": "Wasprogramma 3",
                "WASH_4": "Wasprogramma 1 (bus)",
                "WASH_5": "Wasprogramma 2 (bus)",
                "WASH_6": "Wasprogramma 3 (bus)"
            },
            "margins": {
                "WASH": 0.5,
                "TOPUP_20": 0.5,
                "TOPUP_50": 1,
                "TOPUP_100": 2,
                "TOPUP_200": 4
            },
            "prices": {
                "WASH_1": 15,
                "WASH_2": 12,
                "WASH_3": 9.5,
                "WASH_4": 17,
                "WASH_5": 14,
                "WASH_6": 12,
                "TOPUP_20": 19,
                "TOPUP_50": 47.5,
                "TOPUP_100": 95,
                "TOPUP_200": 190
            },
            "gpio": {
                "errorInput": 17,
                "busyInput": 22,
                "highVehicle": 4,
                "stopVehicle": 27,
                "BIT1LED": 5,
                "BIT2LED": 6,
                "BIT4LED": 13,
                "BIT8LED": 19
            },
            "paynl": {
                "serviceId": "SL-7547-5133",
                "apiToken": "1b3188cd601dd2fb11b3ef512d5bab3c288fad92",
                "tokenCode": "AT-0098-4504",
                "terminalId": "TH-9138-0780",
                "terminalIds": [
                    "TH-9138-0780"
                ],
                "merchantId": "M-7472-3132",
                "debug": "true",
                "paymentOptionId": 1927,
                "timeOut": 20
            }
        }

        # Create a Carwash instance with the mock settings
        carwash = Carwash(mock_settings)

        # Call a method that sets up the GPIO pins
        carwash.run()

        # Assertions to check if the correct methods were called with the correct arguments
        mock_instance.set_mode.assert_any_call(17, mock_instance.OUTPUT)
        # mock_instance.set_mode.assert_any_call(18, mock_instance.OUTPUT)
        # mock_instance.set_mode.assert_any_call(23, mock_instance.INPUT)
        # mock_instance.set_pull_up_down.assert_any_call(23, mock_instance.PUD_DOWN)


if __name__ == '__main__':
    unittest.main()
