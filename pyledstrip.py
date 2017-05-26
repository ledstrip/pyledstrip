"""This module wraps UDP streaming of color information
to WS2812 LED strips connected to an ESP8266 running the
firmware from https://github.com/cnlohr/esp8266ws2812i2s"""

import colorsys
import socket

# data config
_DATA_OFFSET = 3
_R_OFFSET = 1
_G_OFFSET = 0
_B_OFFSET = 2

# connection config
_DEFAULT_IP = "192.168.4.1"
_DEFAULT_PORT = 7777

# LED strip config
LED_COUNT = 300
_AVG_BRIGHTNESS_MAX = 0.2  # used to limit total power when running the LED strip on a small power source
_TOTAL_BRIGHTNESS_MAX = LED_COUNT * _AVG_BRIGHTNESS_MAX

# module variables
_pixels = [[0.0, 0.0, 0.0]] * LED_COUNT
_transmit_buffer = bytearray(LED_COUNT * 3 + _DATA_OFFSET)
_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def set_pixel_rgb(pos: int, r: float, g: float, b: float):
	"""Set floating point rgb values at integer position."""
	global _pixels
	if 0 <= pos < LED_COUNT:
		_pixels[pos] = [r, g, b]


def add_pixel_rgb(pos: int, r: float, g: float, b: float):
	"""Add floating point rgb values at integer position."""
	global _pixels
	if 0 <= pos < LED_COUNT:
		_pixels[pos] = [x + y for x, y in zip(_pixels[pos], [r, g, b])]


def set_rgb(pos: float, r: float, g: float, b: float):
	# split for non-integer position
	pos_floor = int(pos)
	pos_ceil = int(pos + 1.0)
	floor_factor = 1.0 - (pos - pos_floor)
	ceil_factor = 1.0 - (pos_ceil - pos)
	set_pixel_rgb(pos_floor, r * floor_factor, g * floor_factor, b * floor_factor)
	set_pixel_rgb(pos_ceil, r * ceil_factor, g * ceil_factor, b * ceil_factor)


def add_rgb(pos: float, r: float, g: float, b: float):
	# split for non-integer position
	pos_floor = int(pos)
	pos_ceil = int(pos + 1.0)
	floor_factor = 1.0 - (pos - pos_floor)
	ceil_factor = 1.0 - (pos_ceil - pos)
	add_pixel_rgb(pos_floor, r * floor_factor, g * floor_factor, b * floor_factor)
	add_pixel_rgb(pos_ceil, r * ceil_factor, g * ceil_factor, b * ceil_factor)


def set_hsv(pos: float, h: float, s: float, v: float):
	rgb = colorsys.hsv_to_rgb(h, s, v)
	set_rgb(pos, rgb[0], rgb[1], rgb[2])


def add_hsv(pos: float, h: float, s: float, v: float):
	rgb = colorsys.hsv_to_rgb(h, s, v)
	add_rgb(pos, rgb[0], rgb[1], rgb[2])


def clear():
	"""Set all pixels to black. Needs call to transmit() to take effect."""
	for pos in range(0, LED_COUNT):
		set_pixel_rgb(pos, 0, 0, 0)


def _clamp(min_value, value, max_value):
	"""Clamp value to range(min_value, max_value) including limits."""
	return max(min_value, min(value, max_value))


def _limit_total_brightness():
	"""Clamp colors to range(0.0, 1.0) and limit total brightness (power) to _TOTAL_BRIGHTNESS_MAX."""
	global _pixels
	# clamp and sum total brightness
	total_brightness = 0.0
	for pos in range(0, LED_COUNT):
		for c in range(0, 3):
			# clamp individual colors, change here to prevent color change towards white when limiting added colors
			_pixels[pos][c] = _clamp(0.0, _pixels[pos][c], 1.0)
			total_brightness += _pixels[pos][c]
	# limit total brightness
	if total_brightness > _TOTAL_BRIGHTNESS_MAX:
		brightness_factor = _TOTAL_BRIGHTNESS_MAX / total_brightness
		for pos in range(0, LED_COUNT):
			for c in range(0, 3):
				_pixels[pos][c] *= brightness_factor


def _update_buffer():
	"""Convert colors to buffer before transmit."""
	global _pixels
	global _transmit_buffer
	for pos in range(0, LED_COUNT):
		pos_offset = pos * 3 + _DATA_OFFSET
		_transmit_buffer[pos_offset + _R_OFFSET] = _clamp(0, int(_pixels[pos][0] * 255), 255)
		_transmit_buffer[pos_offset + _G_OFFSET] = _clamp(0, int(_pixels[pos][1] * 255), 255)
		_transmit_buffer[pos_offset + _B_OFFSET] = _clamp(0, int(_pixels[pos][2] * 255), 255)


def transmit(ip=_DEFAULT_IP, port=_DEFAULT_PORT):
	"""Limit total brightness, update buffer and transmit to LED strip."""
	global _sock
	global _transmit_buffer
	_limit_total_brightness()
	_update_buffer()
	_sock.sendto(_transmit_buffer, (ip, port))


def off(ip=_DEFAULT_IP, port=_DEFAULT_PORT):
	"""Quickly turn off LED strip."""
	clear()
	transmit(ip, port)


if __name__ == "__main__":
	print("module not intended for execution")
