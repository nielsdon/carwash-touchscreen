"""The Main application for the touchscreen"""
import locale
import logging
import signal
import sys
from carwash import Carwash

locale.setlocale(locale.LC_ALL, 'nl_NL.UTF-8')


def signalHandler(sig, frame, carwash):
    """this runs when program is shut down"""
    logging.debug("Cleaning up GPIO ports")
    carwash.clean_up()
    logging.debug("Exiting....")
    sys.exit(0)


if __name__ == '__main__':
    carwash = Carwash()
    signal.signal(signal.SIGINT, lambda sig, frame: signalHandler(sig, frame, carwash))
    carwash.run()
