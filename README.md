# pyledstrip
Python interface for streaming color information to a WS2812 LED strip connected to an ESP8266 running the firmware from
https://github.com/cnlohr/esp8266ws2812i2s

## Installation
Using `git clone`
```bash
git clone https://github.com/cipold/pyledstrip
cd pyledstrip
python setup.py install
```

## How to use
A simple script which sets the strip to rainbow colors.
```python
from pyledstrip import LedStrip

# Setup LED strip
strip = LedStrip()

# Set rainbow
for pos in range(strip.led_count):
	strip.set_hsv(pos, pos / strip.led_count, 1.0, 1.0)

# Actually transmit the information to the LED strip
strip.transmit()
```

This example shows how to turn off all LEDs.
```python
from pyledstrip import LedStrip

# Setup LED strip
strip = LedStrip()

# Clear all LEDs and transmit
strip.off()
```

## Examples
More examples how this module is used can be found here:
https://github.com/cipold/pyledstrip-examples