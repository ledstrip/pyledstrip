#!/usr/bin/env python
# coding: utf-8

"""
This module wraps UDP streaming of color information
to WS2812 LED strips connected to an ESP8266 running the
firmware from https://github.com/cnlohr/esp8266ws2812i2s
"""

__all__ = ['LedStrip']
__version__ = '2.1'
__author__ = 'Michael Cipold'
__email__ = 'github@cipold.de'
__license__ = 'MPL-2.0'

import colorsys
import configparser
import pprint
import socket
from typing import Union, Callable, List


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
		def set_internal_led_count(c):
			assert (c > 0)
			if c != self._led_count:
				self._led_count = c
				self._pixels = [[0.0, 0.0, 0.0]] * self._led_count
				self._dirty = True

		if isinstance(led_count, list):
			set_internal_led_count(sum(led_count))
			self._led_counts = led_count
			self._transmit_buffers = [bytearray(c * 3 + self.DATA_OFFSET) for c in led_count]
		elif isinstance(led_count, int):
			set_internal_led_count(led_count)
			self._led_counts = [led_count]
			self._transmit_buffers = [bytearray(self._led_count * 3 + self.DATA_OFFSET)]
		else:
			raise ValueError('unexpected led_count type')

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
	_led_counts = 0
	_power_limit = 0.0
	_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	_pixels = None
	_transmit_buffers = None
	_dirty = True

	def __init__(
			self,
			*,
			config: Union[str, configparser.ConfigParser] = None,
			led_count: Union[int, List[int]] = None,
			ip: Union[str, List[str]] = None,
			port: Union[int, List[int]] = None,
			flip: Union[bool, List[bool]] = None,
			power_limit: float = None,
			loop: bool = None,
			args=None
	):
		"""
		:param config: configuration file
		:param led_count: amount of LEDs (used for power and loop calculation)
		:param ip: IP address used when transmit is called
		:param port: UDP port used when transmit is called
		:param flip: Flip LED positions, use led_count - pos - 1 as position
		:param power_limit: limit power use running the LED strip on a small power source
		:param loop: loop positions modulo led_count
		:param args: argparse arguments
		"""

		# Defaults
		self.led_count = 300
		self.power_limit = 0.2
		self.ip = '192.168.4.1'
		self.port = 7777
		self.flip = False

		self.set_parameters(
			config=config,
			led_count=led_count,
			ip=ip,
			port=port,
			flip=flip,
			power_limit=power_limit,
			loop=loop,
			args=args
		)

	def set_parameters(
			self,
			*,
			config: Union[str, configparser.ConfigParser] = None,
			led_count: Union[int, List[int]] = None,
			ip: Union[str, List[str]] = None,
			port: Union[int, List[int]] = None,
			flip: Union[bool, List[bool]] = None,
			power_limit: float = None,
			loop: bool = False,
			args=None
	) -> None:
		"""
		:param config: configuration file
		:param led_count: amount of LEDs (used for power and loop calculation)
		:param ip: IP address used when transmit is called
		:param port: UDP port used when transmit is called
		:param flip: Flip LED positions, use led_count - pos - 1 as position
		:param power_limit: used to limit power use when running the LED strip on a small power source
		:param loop: loop positions modulo led_count
		:param args: argparse arguments
		"""
		if args is not None and args.config is not None:
			self.read_config(args.config)

		if config is not None:
			self.read_config(config)

		if args is not None:
			self.read_args(args)

		if led_count is not None:
			self.led_count = led_count

		if ip is not None:
			self.ip = ip

		if port is not None:
			self.port = port

		if flip is not None:
			self.flip = flip

		if power_limit is not None:
			self.power_limit = power_limit

		if loop is not None:
			self.loop = loop

	def read_config(self, config: Union[str, configparser.ConfigParser]) -> None:
		"""
		:param config: configuration file
		"""
		if isinstance(config, str):
			# Assume config file name was passed
			config_file = config
			config = configparser.ConfigParser()
			config.read(config_file)

		if 'pyledstrip' not in config:
			print('Section "pyledstrip" not found in config')
			return

		section = config['pyledstrip']

		if 'led_count' in section:
			self.led_count = section.getint('led_count')

		if 'ip' in section:
			self.ip = section.get('ip')

		if 'port' in section:
			self.port = section.getint('port')

		if 'power_limit' in section:
			self.power_limit = section.getfloat('power_limit')

		if 'loop' in section:
			self.loop = section.getboolean('loop')

	def read_args(self, args) -> None:
		"""
		:param args: argparse arguments
		"""
		if args.led_count is not None:
			self.led_count = args.led_count

		if args.ip is not None:
			self.ip = args.ip

		if args.port is not None:
			self.port = args.port

		if args.flip is not None:
			self.flip = args.flip

		if args.power_limit is not None:
			self.power_limit = args.power_limit

		if args.loop is not None:
			self.loop = args.loop

	def __str__(self):
		return pprint.pformat({
			'LED Count': self.led_count,
			'IP': self.ip,
			'Port': self.port,
			'Flip': self.flip,
			'Power Limit': self.power_limit,
			'Loop': self.loop,
		})

	def set_pixel_rgb(self, pos: int, red: float, green: float, blue: float) -> None:
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

	def add_pixel_rgb(self, pos: int, red: float, green: float, blue: float) -> None:
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

	def set_rgb(self, pos: float, red: float, green: float, blue: float) -> None:
		"""
		Set floating point rgb values at floating point position (interpolated automatically).
		:param pos: floating point led position
		:param red: red value in range(0.0, 1.0)
		:param green: green value in range(0.0, 1.0)
		:param blue: blue value in range(0.0, 1.0)
		"""
		self._call_interpolated(self.set_pixel_rgb, pos, red, green, blue)

	def add_rgb(self, pos: float, red: float, green: float, blue: float) -> None:
		"""
		Add floating point rgb values at floating point position (interpolated automatically).
		:param pos: floating point led position
		:param red: red value in range(0.0, 1.0)
		:param green: green value in range(0.0, 1.0)
		:param blue: blue value in range(0.0, 1.0)
		"""
		self._call_interpolated(self.add_pixel_rgb, pos, red, green, blue)

	def set_hsv(self, pos: float, hue: float, saturation: float, value: float) -> None:
		"""
		Set floating point hsv values at floating point position (interpolated automatically).
		:param pos: floating point led position
		:param hue: hue value in range(0.0, 1.0)
		:param saturation: saturation value in range(0.0, 1.0)
		:param value: brightness value in range(0.0, 1.0)
		"""
		rgb = colorsys.hsv_to_rgb(hue, saturation, value)
		self.set_rgb(pos, rgb[0], rgb[1], rgb[2])

	def add_hsv(self, pos: float, hue: float, saturation: float, value: float) -> None:
		"""
		Add floating point hsv values at floating point position (interpolated automatically).
		:param pos: floating point led position
		:param hue: hue value in range(0.0, 1.0)
		:param saturation: saturation value in range(0.0, 1.0)
		:param value: brightness value in range(0.0, 1.0)
		"""
		rgb = colorsys.hsv_to_rgb(hue, saturation, value)
		self.add_rgb(pos, rgb[0], rgb[1], rgb[2])

	def clear(self) -> None:
		"""
		Set all pixels to black. Needs call to transmit() to take effect.
		"""
		for pos in range(0, self.led_count):
			self.set_pixel_rgb(pos, 0, 0, 0)

	def _update_buffers(self) -> None:
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

		if not isinstance(self.flip, list):
			self.flip = [self.flip]

		led_index = []
		led_positions = []

		for i, c in enumerate(self._led_counts):
			led_index += [i] * c
			led_positions.extend(list(range(c)[::-1] if self.flip[min(i, len(self.flip) - 1)] else range(c)))

		# update transmit buffer
		for pos in range(self.led_count):
			pos_offset = led_positions[pos] * 3 + self.DATA_OFFSET
			pixel = pixels[pos]
			transmit_buffer = self._transmit_buffers[led_index[pos]]
			transmit_buffer[pos_offset + self.RED_OFFSET] = max(0, min(int(pixel[0] * 255), 255))
			transmit_buffer[pos_offset + self.GREEN_OFFSET] = max(0, min(int(pixel[1] * 255), 255))
			transmit_buffer[pos_offset + self.BLUE_OFFSET] = max(0, min(int(pixel[2] * 255), 255))

		self._dirty = False

	def transmit(self, ip=None, port=None):
		"""
		Update buffer and transmit to LED strip.
		:param ip: Transmit data to this IP address instead of the one specified on init
		:param port: Transmit data to this UDP port instead of the one specified on init
		"""
		if self._dirty:
			self._update_buffers()

		local_ips = self.ip if ip is None else ip
		if not isinstance(local_ips, list):
			local_ips = [local_ips]

		local_ports = self.port if port is None else port
		if not isinstance(local_ports, list):
			local_ports = [local_ports]

		for i, local_ip in enumerate(local_ips):
			self._sock.sendto(
				self._transmit_buffers[i],
				(
					local_ip,
					local_ports[min(i, len(local_ports) - 1)]
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
	def _call_interpolated(
			pixel_func: Callable[[float, float, float, float], None],
			pos: float,
			red: float,
			green: float,
			blue: float
	) -> None:
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

	@staticmethod
	def add_arguments(parser: argparse.ArgumentParser) -> None:
		group = parser.add_argument_group(title='pyledstrip')
		group.add_argument('--config', type=str, help='configuration file')
		group.add_argument('--led_count', type=int, nargs='+', help='amount of LEDs')
		group.add_argument('--ip', type=str, nargs='+', help='IP address')
		group.add_argument('--port', type=int, nargs='+', help='UDP port')
		group.add_argument('--flip', type=bool, nargs='+', help='flip led positions')
		group.add_argument('--power_limit', type=float, help='limit power use')
		group.add_argument('--loop', type=bool, help='loop positions modulo led_count')
