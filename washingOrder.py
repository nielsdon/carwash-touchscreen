import configparser
import logging

CONFIG = configparser.ConfigParser()
CONFIG.read('config.ini')
logging.basicConfig(encoding='utf-8', level=int(CONFIG.get('General','logLevel')))

class Order():
  program = 0
  description = ''
  price = 0
  id = 0
  
  def __init__(self, program):
    self.program = program
    self.description = "Wasprogramma " +str(program)
    prices = CONFIG.get('General','prices').split(',')
    self.amount = float(prices[program])    
      
    #determine order ID
    try:
      file = open('orderId.txt', 'r+')
      read = file.read()
      logging.debug('orderId: ' +read)
      if read:
        self.id = int(read)
      logging.debug('Gevonden order id: ' +str(self.id))
      self.id += 1
      file.seek(0)
      file.write(str(self.id))
      logging.debug('Nieuw order id: ' +str(self.id))
    finally:
      file.close()
