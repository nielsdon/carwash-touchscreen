"""A Helper class to structure the washing orders"""
import logging
from datetime import datetime, time

SETTINGS = {}


class Order():
    """The order being processed"""
    program = ''
    description = ''
    transaction_type = ''
    amount = 0
    margin = 0
    id = 0
    transaction_id = 0

    def __init__(self, program, settings):
        self.program = program
        globals()["SETTINGS"] = settings
        logging.basicConfig(encoding='utf-8', level=int(SETTINGS["general"]["logLevel"]))

        # get the description
        if "names" in SETTINGS and program in SETTINGS["names"]:
            self.description = SETTINGS["names"][program]
        else:
            self.description = "Wasprogramma " + str(program)
        # get the transaction type
        self.transaction_type = program.split("_")[0]

        # additional price for manned days
        uptick = self.get_uptick()

        # determine the price
        self.amount = float(SETTINGS["prices"][program]) + float(uptick)
        print("Price: "
              + str(SETTINGS["prices"][program])
              + " + "
              + str(uptick)
              + " = "
              + str(self.amount))

        # determine the margin
        self.margin = float(SETTINGS["margins"][self.transaction_type])

        # determine order ID
        try:
            file = open('orderId.txt', 'r+', encoding='utf-8')
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

    def get_uptick(self):
        """ determine price uptick based on manned days """
        # Get the current datetime
        now = datetime.now()
        currentWeekday = now.weekday()
        currentTime = now.time()
        mannedDays = SETTINGS["general"]["mannedDays"]
        logging.debug("Current time: %s", currentTime)
        logging.debug("Current current_weekday: %s", str(currentWeekday))

        for day in mannedDays:
            logging.debug("Day:")
            logging.debug(day)
            logging.debug("Comparing weekday %s and %s", str(day["weekday"]), str(currentWeekday))
            if day["weekday"] == currentWeekday:
                if "start" in day and "end" in day:
                    if self.is_within_time_range(day["start"], day["end"], currentTime):
                        print("The current date and time are within the manned time ranges.")
                        return SETTINGS["general"]["mannedUptick"]
        print("The current date and time are not within the manned time ranges.")
        return 0

    # Function to check if current time is within range
    def is_within_time_range(self, start, end, current_time):
        """ helper function to determine if current time is between two times """
        startTime = time.fromisoformat(start)
        endTime = time.fromisoformat(end)
        return startTime <= current_time <= endTime
