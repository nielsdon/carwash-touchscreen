"""A Helper class to structure the washing orders"""
import configparser
import logging
from datetime import datetime

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
SETTINGS = {}

class Order():
    """The order being processed"""
    program = 0
    description = ''
    transaction_type = ''
    amount = 0
    id = 0

    def __init__(self, program, settings):
        self.program = program
        globals()["SETTINGS"] = settings
        logging.basicConfig(encoding='utf-8', level=int(SETTINGS["general"]["logLevel"]))

        # get the description
        if "names" in SETTINGS and program in SETTINGS["names"]:
            self.description = SETTINGS["names"][program]
        else:
            self.description = "Wasprogramma " +str(program)
        # get the transaction type
        self.transaction_type = program.split("_")[0]

        #additional price for manned days
        uptick = 0
        if "mannedDays" in SETTINGS["general"]:
            now = datetime.now()
            # Get the weekday number (0 = Monday, 1 = Tuesday, ..., 6 = Sunday)
            weekday_number = now.weekday()
            logging.info("Manned days applicable, checking if today is manned day...")
            if weekday_number in SETTINGS["general"]["mannedDays"]:
                uptick = SETTINGS["general"]["mannedUptick"]
                logging.info("Yes: Uptick is €%s", str(uptick))
            else:
                logging.info("Nope!")
        else:
            logging.info("No uptick today")

        # determine the price
        self.amount = float(SETTINGS["prices"][program]) + float(uptick)

        # determine order ID
        try:
            file = open('orderId.txt', 'r+')
            read = file.read()
            logging.debug('orderId: %s', read)
            if read:
                self.id = int(read)
            logging.debug('Found order id: %s', str(self.id))
            self.id += 1
            file.seek(0)
            file.write(str(self.id))
            logging.debug('New order id: %s', str(self.id))
        finally:
            file.close()
