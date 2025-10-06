import RPi.GPIO as GPIO

# Initialize GPIO
class LedControl:
    def __init__(self):
        # Connect GPIO pins int with LED names
        GPIO.setmode(GPIO.BCM)
        self.pins = {
            'white': [23, 24],
            'red': [8, 7],
            'green': [12, 16],
            'blue': [20, 21]
        }
        for pins in self.pins.values():
            GPIO.setup(pins, GPIO.OUT)
        self.turn_all_off()
    
    def toggle(self, color):
        pin_pair = self.pins.get(color, [])
        if pin_pair:
            for pin in pin_pair:
                GPIO.output(pin, not GPIO.input(pin))

    def turn_all_off(self):
        for pin in self.pins.values():
            GPIO.output(pin, GPIO.LOW)
            
    def cleanup(self):
        self.turn_all_off()
        GPIO.cleanup()