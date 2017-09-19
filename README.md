# pyledstrip
Python interface for streaming color information to a WS2812 LED strip connected to an ESP8266 running the firmware from
https://github.com/cnlohr/esp8266ws2812i2s

## Installation
```bash
cd pyledstrip
python setup.py install
```

## How to use
```python
import pyledstrip

# Set Rainbow
ledcount = 300
for i in range(ledcount):
	pyledstrip.set_hsv(i, i / ledcount, 1.0, 1.0)

# Actually transmit the information to the LED strip
pyledstrip.transmit()

# Turn LED strip off
pyledstrip.off()
```

## Examples
https://github.com/cipold/pyledstrip-examples