"""The Main application for the touchscreen"""
import locale
import logging
import signal
import sys

from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.logger import Logger

from carwash import Carwash

locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')

def signal_handler(sig, frame, carwash):
    logging.debug("Cleaning up GPIO ports")
    carwash.cleanUp()
    logging.debug("Exiting....")
    sys.exit(0)

if __name__ == '__main__':
    carwash = Carwash()
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, carwash))
    carwash.run()
