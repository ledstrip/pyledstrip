#!/usr/bin/env python
# coding: utf-8

"""
This module wraps UDP streaming of color information
to WS2812 LED strips connected to an ESP8266 running the
firmware from https://github.com/cnlohr/esp8266ws2812i2s
"""

import colorsys
import pprint
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

	# Public variables
	def set_led_count(self, led_count):
		assert (led_count > 0)
		if led_count != self._led_count:
			self._led_count = led_count
			self._pixels = [[0.0, 0.0, 0.0]] * self._led_count
			self._transmit_buffer = bytearray(self._led_count * 3 + self.DATA_OFFSET)
			self._dirty = True

	def set_power_limit(self, power_limit):
		assert (power_limit >= 0.0)
		assert (power_limit <= 1.0)
		self._power_limit = power_limit
		self._dirty = True

	led_count = property(
		fget=lambda self: self._led_count, fset=set_led_count, doc="Amount of LEDs"
	)
	ip = None
	port = None
	power_limit = property(
		fget=lambda self: self._power_limit, fset=set_power_limit, doc="Limit total power used by LED strip"
	)
	loop = False

	# Private variables
	_led_count = 0
	_power_limit = 0.0
	_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	_pixels = None
	_transmit_buffer = None
	_dirty = True

	def __init__(self, led_count=None, ip=None, port=None, power_limit=None, loop=None):
		"""
		:param led_count: amount of LEDs (used for power and loop calculation)
		:param ip: IP address used when transmit is called
		:param port: UDP port used when transmit is called
		:param power_limit: limit power use running the LED strip on a small power source
		:param loop: loop positions modulo led_count
		"""

		# Defaults
		self.led_count = 300
		self.power_limit = 1.0
		self.ip = '192.168.4.1'
		self.port = 7777

		self.set_parameters(led_count=led_count, ip=ip, port=port, power_limit=power_limit, loop=loop)
	def set_parameters(self, led_count=None, ip=None, port=None, power_limit=None, loop=False):
		"""
		:param led_count: amount of LEDs (used for power and loop calculation)
		:param ip: IP address used when transmit is called
		:param port: UDP port used when transmit is called
		:param power_limit: used to limit power use when running the LED strip on a small power source
		:param loop: loop positions modulo led_count
		"""
		if led_count is not None:
			self.led_count = led_count

		if ip is not None:
			self.ip = ip

		if port is not None:
			self.port = port

		if power_limit is not None:
			self.power_limit = power_limit

		if loop is not None:
			self.loop = loop

	def __str__(self):
		return pprint.pformat({
			'LED Count': self.led_count,
			'IP': self.ip,
			'Port': self.port,
			'Power Limit': self.power_limit,
			'Loop': self.loop,
		})

	def set_pixel_rgb(self, pos: int, red: float, green: float, blue: float):
		"""
		Set floating point rgb values at integer position.
		:param pos: integer led position
		:param red: red value in range(0.0, 1.0)
		:param green: green value in range(0.0, 1.0)
		:param blue: blue value in range(0.0, 1.0)
		"""
		if self.loop:
			pos %= self.led_count

		if 0 <= pos < self.led_count:
			self._pixels[pos] = [red, green, blue]
			self._dirty = True

	def add_pixel_rgb(self, pos: int, red: float, green: float, blue: float):
		"""
		Add floating point rgb values at integer position.
		:param pos: integer led position
		:param red: red value in range(0.0, 1.0)
		:param green: green value in range(0.0, 1.0)
		:param blue: blue value in range(0.0, 1.0)
		"""
		if self.loop:
			pos %= self.led_count

		if 0 <= pos < self.led_count:
			self._pixels[pos] = list(map(lambda a, b: a + b, self._pixels[pos], [red, green, blue]))
			self._dirty = True

	def set_rgb(self, pos: float, red: float, green: float, blue: float):
		"""
		Set floating point rgb values at floating point position (interpolated automatically).
		:param pos: floating point led position
		:param red: red value in range(0.0, 1.0)
		:param green: green value in range(0.0, 1.0)
		:param blue: blue value in range(0.0, 1.0)
		"""
		self._call_interpolated(self.set_pixel_rgb, pos, red, green, blue)

	def add_rgb(self, pos: float, red: float, green: float, blue: float):
		"""
		Add floating point rgb values at floating point position (interpolated automatically).
		:param pos: floating point led position
		:param red: red value in range(0.0, 1.0)
		:param green: green value in range(0.0, 1.0)
		:param blue: blue value in range(0.0, 1.0)
		"""
		self._call_interpolated(self.add_pixel_rgb, pos, red, green, blue)

	def set_hsv(self, pos: float, hue: float, saturation: float, value: float):
		"""
		Set floating point hsv values at floating point position (interpolated automatically).
		:param pos: floating point led position
		:param hue: hue value in range(0.0, 1.0)
		:param saturation: saturation value in range(0.0, 1.0)
		:param value: brightness value in range(0.0, 1.0)
		"""
		rgb = colorsys.hsv_to_rgb(hue, saturation, value)
		self.set_rgb(pos, rgb[0], rgb[1], rgb[2])

	def add_hsv(self, pos: float, hue: float, saturation: float, value: float):
		"""
		Add floating point hsv values at floating point position (interpolated automatically).
		:param pos: floating point led position
		:param hue: hue value in range(0.0, 1.0)
		:param saturation: saturation value in range(0.0, 1.0)
		:param value: brightness value in range(0.0, 1.0)
		"""
		rgb = colorsys.hsv_to_rgb(hue, saturation, value)
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
	def _call_interpolated(pixel_func, pos: float, red: float, green: float, blue: float):
		"""
		Helper function distributing a color manipulation between two pixels based on interpolation.
		:param pixel_func: function manipulating a single pixel
		:param pos: floating point led position
		:param red: red value in range(0.0, 1.0)
		:param green: green value in range(0.0, 1.0)
		:param blue: blue value in range(0.0, 1.0)
		"""
		pos_floor = int(pos)
		pos_ceil = int(pos + 1.0)
		floor_factor = 1.0 - (pos - pos_floor)
		ceil_factor = 1.0 - (pos_ceil - pos)
		pixel_func(pos_floor, red * floor_factor, green * floor_factor, blue * floor_factor)
		pixel_func(pos_ceil, red * ceil_factor, green * ceil_factor, blue * ceil_factor)
