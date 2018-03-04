#!/usr/bin/env python
# coding: utf-8

"""
This module wraps streaming of color information to WS2812 LED strips
"""

__all__ = ['LedStrip']
__version__ = '2.1'
__author__ = 'Michael Cipold'
__email__ = 'github@cipold.de'
__license__ = 'MPL-2.0'

import argparse
import colorsys
import configparser
import pprint
import shlex
import socket
from typing import Union, Callable, List


class Protocol:
    pass


# Protocol specified by ESP8266 I2S WS2812 Driver
# https://github.com/cnlohr/esp8266ws2812i2s
class ProtocolEsp(Protocol):
    CONNECTION_TYPE = 'udp'
    DATA_OFFSET = 3
    RED_OFFSET = 1
    GREEN_OFFSET = 0
    BLUE_OFFSET = 2
    LED_COUNT_HIGH_BYTE = None
    LED_COUNT_LOW_BYTE = None


# Protocol specified by Open Pixel Control
# http://openpixelcontrol.org
class ProtocolOpc(Protocol):
    CONNECTION_TYPE = 'tcp'
    DATA_OFFSET = 4
    RED_OFFSET = 0
    GREEN_OFFSET = 1
    BLUE_OFFSET = 2
    LED_COUNT_HIGH_BYTE = 2
    LED_COUNT_LOW_BYTE = 3


PROTOCOLS = {
    'esp': ProtocolEsp,
    'opc': ProtocolOpc,
}


class LedStrip:
    """
    Class managing led strip state information (e.g. connection information, color information before transmit)
    """

    def _refresh_parameters(self) -> None:
        """
        Build consistent parameter list from possibly ambiguous user inputs
        """
        # Transform all strip parameters for lists
        if isinstance(self._led_count, int):
            self._led_counts = [self._led_count]
        else:
            self._led_counts = self._led_count

        if isinstance(self._ip, str):
            self._ips = [self._ip]
        else:
            self._ips = self._ip

        if isinstance(self._port, int):
            self._ports = [self._port]
        else:
            self._ports = self._port

        if isinstance(self._protocol, List):
            self._protocols = self._protocol
        else:
            self._protocols = [self._protocol]

        self._protocols = [PROTOCOLS[p] if isinstance(p, str) else p for p in self._protocols]

        if isinstance(self._flip, bool):
            self._flips = [self._flip]
        else:
            self._flips = self._flip

        # A strip is defined by a set of ip and port
        self._strip_count = max(len(self._ips), len(self._ports))

        # Make all lists equal in length
        if len(self._ips) < self._strip_count:
            self._ips = self._ips + [self._ips[0]] * (self._strip_count - len(self._ips))

        if len(self._ports) < self._strip_count:
            self._ports = self._ports + [self._ports[0]] * (self._strip_count - len(self._ports))

        if len(self._protocols) < self._strip_count:
            self._protocols = self._protocols + [self._protocols[0]] * (self._strip_count - len(self._protocols))

        if len(self._led_counts) > self._strip_count:
            self._led_counts = self._led_counts[:self._strip_count]
        elif len(self._led_counts) < self._strip_count:
            self._led_counts = self._led_counts * self._strip_count

        if len(self._flips) > self._strip_count:
            self._flips = self._flips[:self._strip_count]
        elif len(self._flips) < self._strip_count:
            self._flips = self._flips * self._strip_count

        if self._total_led_count != sum(self._led_counts):
            self._total_led_count = sum(self._led_counts)
            self._pixels = [[0.0, 0.0, 0.0]] * self._total_led_count

        self._transmit_buffers = [bytearray(c * 3 + self._protocols[i].DATA_OFFSET) for i, c in
                                  enumerate(self._led_counts)]
        self._transmit_buffers_dirty = True
        self._socks = [None for _ in self._led_counts]

        self._strip_index = []
        self._strip_positions = []

        for i, c in enumerate(self._led_counts):
            self._strip_index += [i] * c
            self._strip_positions.extend(list(range(c)[::-1] if self._flips[i] else range(c)))

    # Public variables
    def _set_led_count(self, led_count: Union[int, List[int]]) -> None:
        self._led_count = led_count
        self._refresh_parameters()

    led_count = property(
        fget=lambda self: self._total_led_count,
        fset=_set_led_count,
        doc='Amount of LEDs'
    )

    def _set_ip(self, ip: Union[str, List[str]]) -> None:
        self._ip = ip
        self._refresh_parameters()

    ip = property(
        fget=lambda self: self._ip,
        fset=_set_ip,
        doc='IP address used when transmit is called'
    )

    def _set_port(self, port: Union[int, List[int]]) -> None:
        self._port = port
        self._refresh_parameters()

    port = property(
        fget=lambda self: self._port,
        fset=_set_port,
        doc='Port used when transmit is called'
    )

    def _set_protocol(self, protocol: Union[Protocol, List[Protocol]]) -> None:
        self._protocol = protocol
        self._refresh_parameters()

    protocol = property(
        fget=lambda self: self._protocol,
        fset=_set_protocol,
        doc='Protocol used when transmit is called'
    )

    def _set_flip(self, flip: Union[bool, List[bool]]) -> None:
        self._flip = flip
        self._refresh_parameters()

    flip = property(
        fget=lambda self: self._flip,
        fset=_set_flip,
        doc='Flip LED positions, use led_count - pos - 1 as position'
    )

    def _set_power_limit(self, power_limit: float) -> None:
        assert power_limit >= 0.0
        assert power_limit <= 1.0
        self._power_limit = power_limit
        self._transmit_buffers_dirty = True

    power_limit = property(
        fget=lambda self: self._power_limit,
        fset=_set_power_limit,
        doc='Limit total power used by LED strip'
    )

    def __init__(
            self,
            *,
            config: Union[str, configparser.ConfigParser] = None,
            led_count: Union[int, List[int]] = None,
            ip: Union[str, List[str]] = None,
            port: Union[int, List[int]] = None,
            protocol: Union[Protocol, List[Protocol]] = None,
            flip: Union[bool, List[bool]] = None,
            power_limit: float = None,
            loop: bool = None,
            args=None
    ):
        """
        :param config: configuration file
        :param led_count: amount of LEDs (used for power and loop calculation)
        :param ip: IP address used when transmit is called
        :param port: Port used when transmit is called
        :param protocol: Protocol used when transmit is called
        :param flip: Flip LED positions, use led_count - pos - 1 as position
        :param power_limit: limit power use running the LED strip on a small power source
        :param loop: loop positions modulo led_count
        :param args: argparse arguments
        """

        # Property variables per strip
        self._led_count = 300
        self._ip = '192.168.4.1'
        self._port = 7777
        self._protocol = ProtocolEsp
        self._flip = False

        # Instance variables
        self.loop = False
        self._power_limit = 0.2

        # Misc private variables
        self._socks = None
        self._strip_count = None
        self._total_led_count = None
        self._led_counts = None
        self._ips = None
        self._ports = None
        self._protocols = None
        self._flips = None
        self._pixels = None
        self._transmit_buffers = None
        self._transmit_buffers_dirty = True
        self._strip_index = None
        self._strip_positions = None

        self._refresh_parameters()

        self.set_parameters(
            config=config,
            led_count=led_count,
            ip=ip,
            port=port,
            protocol=protocol,
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
            protocol: Union[Protocol, List[Protocol]] = None,
            flip: Union[bool, List[bool]] = None,
            power_limit: float = None,
            loop: bool = False,
            args=None
    ) -> None:
        """
        :param config: configuration file
        :param led_count: amount of LEDs (used for power and loop calculation)
        :param ip: IP address used when transmit is called
        :param port: Port used when transmit is called
        :param protocol: Protocol used when transmit is called
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

        if protocol is not None:
            self.protocol = protocol

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
            self.led_count = [int(p) for p in shlex.split(section.get('led_count'))]

        if 'ip' in section:
            self.ip = shlex.split(section.get('ip'))

        if 'port' in section:
            self.port = [int(p) for p in shlex.split(section.get('port'))]

        if 'protocol' in section:
            self.protocol = [PROTOCOLS[p] for p in shlex.split(section.get('protocol'))]

        if 'flip' in section:
            self.flip = [bool(f) for f in shlex.split(section.get('flip'))]

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

        if args.protocol is not None:
            self.protocol = args.protocol

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
            'Protocol': self.protocol,
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
            pos %= self._total_led_count

        if 0 <= pos < self._total_led_count:
            self._pixels[pos] = [red, green, blue]
            self._transmit_buffers_dirty = True

    def add_pixel_rgb(self, pos: int, red: float, green: float, blue: float) -> None:
        """
        Add floating point rgb values at integer position.
        :param pos: integer led position
        :param red: red value in range(0.0, 1.0)
        :param green: green value in range(0.0, 1.0)
        :param blue: blue value in range(0.0, 1.0)
        """
        if self.loop:
            pos %= self._total_led_count

        if 0 <= pos < self._total_led_count:
            self._pixels[pos] = list(map(lambda a, b: a + b, self._pixels[pos], [red, green, blue]))
            self._transmit_buffers_dirty = True

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
        for pos in range(0, self._total_led_count):
            self.set_pixel_rgb(pos, 0, 0, 0)

    def _update_buffers(self) -> None:
        """
        Clamp colors to range(0.0, 1.0), limit power use and convert colors to buffer.
        """

        # clamp individual colors
        pixels = [list(map(lambda color: max(0.0, min(color, 1.0)), pixel)) for pixel in self._pixels]

        # limit power use
        power_use = sum([sum(pixel) / 3 for pixel in pixels]) / self._total_led_count
        if power_use > self._power_limit:
            brightness_factor = self._power_limit / power_use
            pixels = [[color * brightness_factor for color in pixel] for pixel in pixels]

        # update transmit buffer
        for pos in range(self._total_led_count):
            strip_index = self._strip_index[pos]
            protocol = self._protocols[strip_index]
            transmit_buffer = self._transmit_buffers[strip_index]

            if protocol.LED_COUNT_HIGH_BYTE is not None and protocol.LED_COUNT_LOW_BYTE is not None:
                transmit_buffer[protocol.LED_COUNT_HIGH_BYTE] = min(int(self._led_counts[strip_index] / 256), 255)
                transmit_buffer[protocol.LED_COUNT_LOW_BYTE] = self._led_counts[strip_index] % 256

            pixel = pixels[pos]
            pos_offset = self._strip_positions[pos] * 3 + protocol.DATA_OFFSET
            transmit_buffer[pos_offset + protocol.RED_OFFSET] = max(0, min(int(pixel[0] * 255), 255))
            transmit_buffer[pos_offset + protocol.GREEN_OFFSET] = max(0, min(int(pixel[1] * 255), 255))
            transmit_buffer[pos_offset + protocol.BLUE_OFFSET] = max(0, min(int(pixel[2] * 255), 255))

        self._transmit_buffers_dirty = False

    def transmit(self) -> None:
        """
        Update buffer and transmit to LED strip.
        """
        if self._transmit_buffers_dirty:
            self._update_buffers()

        for i in range(self._strip_count):
            protocol = self._protocols[i]
            if not self._socks[i]:
                if protocol.CONNECTION_TYPE == 'udp':
                    self._socks[i] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                else:
                    self._socks[i] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    res = self._socks[i].connect_ex((self._ips[i], self._ports[i]))
                    if res != 0:
                        self._socks[i] = None
                        continue

            if protocol.CONNECTION_TYPE == 'udp':
                self._socks[i].sendto(self._transmit_buffers[i], (self._ips[i], self._ports[i]))
            else:
                try:
                    self._socks[i].sendall(self._transmit_buffers[i])
                except InterruptedError:
                    self._socks[i] = None

    def off(self) -> None:
        """
        Quickly turn off LED strip (clear and transmit).
        """
        self.clear()
        self.transmit()

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
        group.add_argument('--port', type=int, nargs='+', help='Port')
        group.add_argument('--protocol', type=str, nargs='+', help='Protocol')
        group.add_argument('--flip', type=bool, nargs='+', help='flip led positions')
        group.add_argument('--power_limit', type=float, help='limit power use')
        group.add_argument('--loop', type=bool, help='loop positions modulo led_count')
