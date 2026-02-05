import time
import adafruit_pixelbuf
import board
from adafruit_raspberry_pi5_neopixel_write import neopixel_write

class LedControl:
    def __init__(self):
        self.NEOPIXEL = board.D13
        self.num_pixels = 12
        
        # Create the pixel buffer
        self.pixels = self.Pi5Pixelbuf(
            self.NEOPIXEL, 
            self.num_pixels, 
            auto_write=False,
            byteorder="GRB"
        )
        
        # Define colors (R, G, B)
        self.colors = {
            'white': (255, 255, 255),
            'green': (0, 255, 0),
            'red': (255, 0, 0),
            'blue': (0, 0, 255),
            'off': (0, 0, 0)
        }
        
        # Track which colors are currently on
        self.color_states = {
            'white': False,
            'green': False,
            'red': False,
            'blue': False
        }
        
        self.turn_all_off()
    
    class Pi5Pixelbuf(adafruit_pixelbuf.PixelBuf):
        def __init__(self, pin, size, **kwargs):
            self._pin = pin
            super().__init__(size=size, **kwargs)

        def _transmit(self, buf):
            neopixel_write(self._pin, buf)
    
    def toggle(self, color):
        """Toggle a specific color on/off"""
        if color in self.color_states:
            # Toggle the state
            self.color_states[color] = not self.color_states[color]
            
            # If turning on, turn off other colors first
            if self.color_states[color]:
                for other_color in self.color_states:
                    if other_color != color:
                        self.color_states[other_color] = False
                
                # Turn on the selected color
                self.pixels.fill(self.colors[color])
            else:
                # Turn off
                self.pixels.fill(self.colors['off'])
            self.pixels.show()
    
    def set_color(self, color_name):
        """Set all LEDs to a specific color without toggling"""
        if color_name in self.colors:
            self.pixels.fill(self.colors[color_name])
            self.pixels.show()
            
            # Update states
            for c in self.color_states:
                self.color_states[c] = (c == color_name)
    
    def turn_all_off(self):
        """Turn off all LEDs"""
        self.pixels.fill(self.colors['off'])
        self.pixels.show()
        for color in self.color_states:
            self.color_states[color] = False
    
    def set_brightness(self, brightness):
        """Set brightness (0.0 to 1.0)"""
        self.pixels.brightness = max(0.0, min(1.0, brightness))
        self.pixels.show()
    
    def cleanup(self):
        """Turn off LEDs on cleanup"""
        self.turn_all_off()