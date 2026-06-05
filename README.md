# pyledstrip

Python interface for streaming color information to WS2812 LED strips. Supports multiple backends:

- **ESP** (default): UDP to an ESP8266 running [esp8266ws2812i2s](https://github.com/cnlohr/esp8266ws2812i2s)
- **OPC**: TCP using the [Open Pixel Control](http://openpixelcontrol.org) protocol

## Installation

```bash
git clone https://github.com/cipold/pyledstrip.git
cd pyledstrip
python setup.py install
```

## Quick start

```python
from pyledstrip import LedStrip

strip = LedStrip()

for pos in range(strip.led_count):
    strip.set_hsv(pos, pos / strip.led_count, 1.0, 1.0)

strip.transmit()
```

Turn off all LEDs:

```python
from pyledstrip import LedStrip

strip = LedStrip()
strip.off()
```

## Configuration

Parameters can be set via the constructor, a config file, or `argparse` arguments. Defaults:

| Parameter          | Default         | Description                                      |
|--------------------|-----------------|--------------------------------------------------|
| `led_count`        | `300`           | Number of LEDs (int or list of ints per strip)   |
| `ip`               | `192.168.4.1`   | Target IP address (str or list)                  |
| `port`             | `7777`          | Target port (int or list)                        |
| `protocol`         | `esp`           | Protocol: `esp` or `opc` (or list)               |
| `flip`             | `False`         | Reverse LED order (bool or list)                 |
| `power_limit`      | `0.2`           | Max average power (0.0–1.0)                      |
| `brightness_limit` | `1.0`           | Max per-LED brightness (0.0–1.0)                 |
| `brightness_factor`| `1.0`           | Global brightness multiplier (0.0–1.0)           |
| `loop`             | `False`         | Wrap positions modulo `led_count`                |

### Config file

`~/.pyledstrip.ini` is loaded automatically. Additional files can be passed via `config=`.

```ini
[pyledstrip]
led_count = 150
ip = 192.168.1.100
port = 7777
protocol = esp
power_limit = 0.3
brightness_factor = 0.8
```

For multiple strips, space-separate values:

```ini
[pyledstrip]
led_count = 150 150
ip = 192.168.1.100 192.168.1.101
port = 7777 7777
protocol = esp esp
flip = False True
```

### argparse integration

```python
import argparse
from pyledstrip import LedStrip

parser = argparse.ArgumentParser()
LedStrip.add_arguments(parser)
args = parser.parse_args()

strip = LedStrip(args=args)
```

This adds a `pyledstrip` argument group with `--led_count`, `--ip`, `--port`, `--protocol`, `--flip`, `--power_limit`, `--brightness_limit`, `--brightness_factor`, `--loop`, and `--config`.

## API

### Setting colors

All color values are floats in the range `0.0`–`1.0`. Positions can be integer (exact pixel) or float (interpolated across two adjacent pixels).

| Method | Description |
|---|---|
| `set_pixel_rgb(pos, r, g, b)` | Set RGB at integer position |
| `add_pixel_rgb(pos, r, g, b)` | Add RGB at integer position |
| `set_rgb(pos, r, g, b)` | Set RGB at float position (interpolated) |
| `add_rgb(pos, r, g, b)` | Add RGB at float position (interpolated) |
| `set_hsv(pos, h, s, v)` | Set HSV at float position (interpolated) |
| `add_hsv(pos, h, s, v)` | Add HSV at float position (interpolated) |
| `set_pixels_rgb(array)` | Set all pixels at once from an `(N, 3)` numpy array |

### Control

| Method | Description |
|---|---|
| `clear()` | Set all pixels to black (call `transmit()` to apply) |
| `transmit()` | Send current pixel state to the LED strip |
| `off()` | `clear()` + `transmit()` |

## Multiple strips

Pass lists for `led_count`, `ip`, `port`, `protocol`, and `flip` to drive multiple strips simultaneously. The logical pixel space spans all strips concatenated in order.

```python
strip = LedStrip(
    led_count=[150, 150],
    ip=['192.168.1.100', '192.168.1.101'],
    protocol=['esp', 'opc'],
    flip=[False, True],
)
```

## Examples

More usage examples: https://github.com/cipold/pyledstrip-examples
