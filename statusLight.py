"""the class to handloe the RGB led for status info"""
import pigpio

class Status_light():
    red = 0
    green = 0
    blue = 0
    pi = None

    def __init__(self, rgb):
        self.red = rgb[0]
        self.green = rgb[1]
        self.blue = rgb[2]
        self.pi = pigpio.pi()
        if not self.pi.connected:
            exit()
        self.pi.set_mode(self.red, pigpio.OUTPUT)
        self.pi.set_mode(self.green, pigpio.OUTPUT)
        self.pi.set_mode(self.blue, pigpio.OUTPUT)
        self.off()

    def error(self):
        self.pi.write(self.red, 1)
        self.pi.write(self.green, 0)
        self.pi.write(self.blue, 0)

    def busy(self):
        self.pi.write(self.red, 0)
        self.pi.write(self.green, 0)
        self.pi.write(self.blue, 1)

    def starting(self):
        self.pi.write(self.red, 0)
        self.pi.write(self.green, 1)
        self.pi.write(self.blue, 0)

    def stop(self):
        self.pi.write(self.red, 1)
        self.pi.write(self.green, 1)
        self.pi.write(self.blue, 0)
        
    def high(self):
        self.pi.write(self.red, 1)
        self.pi.write(self.green, 0)
        self.pi.write(self.blue, 1)

    def off(self):
        self.pi.write(self.red, 0)
        self.pi.write(self.green, 0)
        self.pi.write(self.blue, 0)