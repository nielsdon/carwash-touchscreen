import unittest
from unittest.mock import patch, MagicMock

# Mock sys.exit and pigpio before importing main.py
with patch('sys.exit'), patch.dict('sys.modules', {'pigpio': MagicMock()}):
    import main


class TestMain(unittest.TestCase):
    @patch('carwash.pigpio.pi')
    def test_carwash_run(self, mock_pi):
        mock_instance = mock_pi.return_value

        # Define mock settings with gpio configuration
        mock_settings = {
            "gpio": {
                "errorInput": 17,
                "busyInput": 22,
                "highVehicle": 4,
                "stopVehicle": 27,
                "BIT1LED": 5,
                "BIT2LED": 6,
                "BIT4LED": 13,
                "BIT8LED": 19
            }
        }
        
        carwash = main.Carwash(mock_settings)
        # Mock the screen manager
        carwash.sm = MagicMock()
        carwash.sm.get_screen.return_value = MagicMock()
        main.signalHandler(None, None, carwash)
        mock_instance.set_mode.assert_any_call(17, mock_instance.OUTPUT)
        mock_instance.set_mode.assert_any_call(18, mock_instance.OUTPUT)

    @patch('sys.exit')
    @patch('carwash.pigpio.pi')
    def test_signal_handler(self, mock_pi, mock_exit):
        mock_instance = mock_pi.return_value
        
        # Define mock settings with gpio configuration
        mock_settings = {
            "gpio": {
                "errorInput": 17,
                "busyInput": 22,
                "highVehicle": 4,
                "stopVehicle": 27,
                "BIT1LED": 5,
                "BIT2LED": 6,
                "BIT4LED": 13,
                "BIT8LED": 19
            }
        }

        carwash = main.Carwash(mock_settings)
        # Mock the screen manager
        carwash.sm = MagicMock()
        carwash.sm.get_screen.return_value = MagicMock()
        main.signalHandler(None, None, carwash)
        mock_instance.stop.assert_called_once()
        mock_exit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
