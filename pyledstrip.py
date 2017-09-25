#!/usr/bin/env python
# coding: utf-8

"""
This module wraps UDP streaming of color information
to WS2812 LED strips connected to an ESP8266 running the
firmware from https://github.com/cnlohr/esp8266ws2812i2s
"""

import colorsys
import socket


class LedStrip:
	"""
	Class managing led strip state information (e.g. connection information, color information before transmit)
	"""

	# Public constants
	DATA_OFFSET = 3
	RED_OFFSET = 1
	GREEN_OFFSET = 0
	BLUE_OFFSET = 2

	def __init__(self, led_count=300, ip='192.168.4.1', port=7777, power_limit=0.2, loop=False):
		"""
		:param led_count: amount of LEDs (used for power and loop calculation)
		:param ip: IP address used when transmit is called
		:param port: UDP port used when transmit is called
		:param power_limit: used to limit power use when running the LED strip on a small power source
		:param loop: allow positions to loop modulo led_count
		"""
		self.led_count = led_count
		self.power_limit = power_limit
		self.ip = ip
		self.port = port
		self.loop = loop

		self._pixels = [[0.0, 0.0, 0.0]] * led_count
		self._transmit_buffer = bytearray(led_count * 3 + self.DATA_OFFSET)
		self._dirty = True
		self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		assert (self.led_count > 0)
		assert (power_limit >= 0.0)
		assert (power_limit <= 1.0)

	def set_pixel_rgb(self, pos: int, r: float, g: float, b: float):
		"""
		Set floating point rgb values at integer position.
		:param pos: integer led position
		:param r: red value in range(0.0, 1.0)
		:param g: green value in range(0.0, 1.0)
		:param b: blue value in range(0.0, 1.0)
		"""
		if self.loop:
			pos %= self.led_count

		if 0 <= pos < self.led_count:
			self._pixels[pos] = [r, g, b]
			self._dirty = True

	def add_pixel_rgb(self, pos: int, r: float, g: float, b: float):
		"""
		Add floating point rgb values at integer position.
		:param pos: integer led position
		:param r: red value in range(0.0, 1.0)
		:param g: green value in range(0.0, 1.0)
		:param b: blue value in range(0.0, 1.0)
		"""
		if self.loop:
			pos %= self.led_count

		if 0 <= pos < self.led_count:
			self._pixels[pos] = list(map(lambda a, b: a + b, self._pixels[pos], [r, g, b]))
			self._dirty = True

	def set_rgb(self, pos: float, r: float, g: float, b: float):
		"""
		Set floating point rgb values at floating point position (interpolated automatically).
		:param pos: floating point led position
		:param r: red value in range(0.0, 1.0)
		:param g: green value in range(0.0, 1.0)
		:param b: blue value in range(0.0, 1.0)
		"""
		self._call_interpolated(self.set_pixel_rgb, pos, r, g, b)

	def add_rgb(self, pos: float, r: float, g: float, b: float):
		"""
		Add floating point rgb values at floating point position (interpolated automatically).
		:param pos: floating point led position
		:param r: red value in range(0.0, 1.0)
		:param g: green value in range(0.0, 1.0)
		:param b: blue value in range(0.0, 1.0)
		"""
		self._call_interpolated(self.add_pixel_rgb, pos, r, g, b)

	def set_hsv(self, pos: float, h: float, s: float, v: float):
		"""
		Set floating point hsv values at floating point position (interpolated automatically).
		:param pos: floating point led position
		:param h: hue value in range(0.0, 1.0)
		:param s: saturation value in range(0.0, 1.0)
		:param v: value value in range(0.0, 1.0)
		"""
		rgb = colorsys.hsv_to_rgb(h, s, v)
		self.set_rgb(pos, rgb[0], rgb[1], rgb[2])

	def add_hsv(self, pos: float, h: float, s: float, v: float):
		"""
		Add floating point hsv values at floating point position (interpolated automatically).
		:param pos: floating point led position
		:param h: hue value in range(0.0, 1.0)
		:param s: saturation value in range(0.0, 1.0)
		:param v: value value in range(0.0, 1.0)
		"""
		rgb = colorsys.hsv_to_rgb(h, s, v)
		self.add_rgb(pos, rgb[0], rgb[1], rgb[2])

	def clear(self):
		"""
		Set all pixels to black. Needs call to transmit() to take effect.
		"""
		for pos in range(0, self.led_count):
			self.set_pixel_rgb(pos, 0, 0, 0)

	def _update_buffer(self):
		"""
		Clamp colors to range(0.0, 1.0), limit power use and convert colors to buffer.
		"""

		# clamp individual colors
		pixels = [list(map(lambda color: max(0.0, min(color, 1.0)), pixel)) for pixel in self._pixels]

		# limit power use
		power_use = sum([sum(pixel) / 3 for pixel in pixels]) / self.led_count
		if power_use > self.power_limit:
			brightness_factor = self.power_limit / power_use
			pixels = [[color * brightness_factor for color in pixel] for pixel in pixels]

		# update transmit buffer
		for pos in range(self.led_count):
			pos_offset = pos * 3 + self.DATA_OFFSET
			pixel = pixels[pos]
			self._transmit_buffer[pos_offset + self.RED_OFFSET] = max(0, min(int(pixel[0] * 255), 255))
			self._transmit_buffer[pos_offset + self.GREEN_OFFSET] = max(0, min(int(pixel[1] * 255), 255))
			self._transmit_buffer[pos_offset + self.BLUE_OFFSET] = max(0, min(int(pixel[2] * 255), 255))

		self._dirty = False

	def transmit(self, ip=None, port=None):
		"""
		Update buffer and transmit to LED strip.
		:param ip: Transmit data to this IP address instead of the one specified on init
		:param port: Transmit data to this UDP port instead of the one specified on init
		"""
		if self._dirty:
			self._update_buffer()

		self._sock.sendto(
			self._transmit_buffer,
			(
				self.ip if ip is None else ip,
				self.port if port is None else port
			)
		)

	def off(self, ip=None, port=None):
		"""
		Quickly turn off LED strip (clear and transmit).
		:param ip: Transmit data to this IP address instead of the one specified on init
		:param port: Transmit data to this UDP port instead of the one specified on init
		"""
		self.clear()
		self.transmit(ip, port)

	@staticmethod
	def _call_interpolated(pixel_func, pos: float, r: float, g: float, b: float):
		"""
		Helper function distributing a color manipulation between two pixels based on interpolation.
		:param pixel_func: function manipulating a single pixel
		:param pos: floating point led position
		:param r: red value in range(0.0, 1.0)
		:param g: green value in range(0.0, 1.0)
		:param b: blue value in range(0.0, 1.0)
		"""
		pos_floor = int(pos)
		pos_ceil = int(pos + 1.0)
		floor_factor = 1.0 - (pos - pos_floor)
		ceil_factor = 1.0 - (pos_ceil - pos)
		pixel_func(pos_floor, r * floor_factor, g * floor_factor, b * floor_factor)
		pixel_func(pos_ceil, r * ceil_factor, g * ceil_factor, b * ceil_factor)
