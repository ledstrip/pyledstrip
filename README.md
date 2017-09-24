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
```python
from pyledstrip import LedStrip

# Setup LED strip
led_count = 300
strip = LedStrip(led_count=led_count)

# Set rainbow
for pos in range(led_count):
	strip.set_hsv(pos, pos / led_count, 1.0, 1.0)

# Actually transmit the information to the LED strip
strip.transmit()

# Turn LED strip off
strip.off()
```

## Examples
More examples how this module is used can be found here:
https://github.com/cipold/pyledstrip-examples