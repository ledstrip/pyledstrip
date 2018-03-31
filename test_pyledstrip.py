#!/usr/bin/env python
# coding: utf-8

import configparser
import unittest

from pyledstrip import LedStrip


class TestParameters(unittest.TestCase):
    def test_single(self):
        strip = LedStrip(led_count=321, ip='123.123.123.123', port=54321, flip=False)
        self.assertEqual([321], strip._led_counts)
        self.assertEqual(['123.123.123.123'], strip._ips)
        self.assertEqual([54321], strip._ports)
        self.assertEqual([False], strip._flips)

    def test_single_lists(self):
        strip = LedStrip(led_count=[321], ip=['123.123.123.123'], port=[54321], flip=[False])
        self.assertEqual([321], strip._led_counts)
        self.assertEqual(['123.123.123.123'], strip._ips)
        self.assertEqual([54321], strip._ports)
        self.assertEqual([False], strip._flips)

    def test_double_lists(self):
        strip = LedStrip(led_count=[321, 1337], ip=['123.123.123.123', '1.1.1.1'], port=[54321, 12345],
                         flip=[True, False])
        self.assertEqual([321, 1337], strip._led_counts)
        self.assertEqual(['123.123.123.123', '1.1.1.1'], strip._ips)
        self.assertEqual([54321, 12345], strip._ports)
        self.assertEqual([True, False], strip._flips)

    def test_partial_1(self):
        strip = LedStrip(led_count=[321, 1337], ip='123.123.123.123', port=54321, flip=False)
        self.assertEqual([321], strip._led_counts)
        self.assertEqual(['123.123.123.123'], strip._ips)
        self.assertEqual([54321], strip._ports)
        self.assertEqual([False], strip._flips)

    def test_partial_2(self):
        strip = LedStrip(led_count=321, ip=['123.123.123.123', '1.1.1.1'], port=54321, flip=False)
        self.assertEqual([321, 321], strip._led_counts)
        self.assertEqual(['123.123.123.123', '1.1.1.1'], strip._ips)
        self.assertEqual([54321, 54321], strip._ports)
        self.assertEqual([False, False], strip._flips)

    def test_partial_3(self):
        strip = LedStrip(led_count=321, ip='123.123.123.123', port=[54321, 12345], flip=False)
        self.assertEqual([321, 321], strip._led_counts)
        self.assertEqual(['123.123.123.123', '123.123.123.123'], strip._ips)
        self.assertEqual([54321, 12345], strip._ports)
        self.assertEqual([False, False], strip._flips)

    def test_partial_4(self):
        strip = LedStrip(led_count=321, ip='123.123.123.123', port=54321, flip=[True, False])
        self.assertEqual([321], strip._led_counts)
        self.assertEqual(['123.123.123.123'], strip._ips)
        self.assertEqual([54321, ], strip._ports)
        self.assertEqual([True, ], strip._flips)


class TestBufferAssembly(unittest.TestCase):

    def setUp(self):
        self.config = configparser.ConfigParser()
        self.config['pyledstrip'] = {
            'protocol': 'esp',
            'power_limit': 1.0,
        }

    def test_simple(self):
        strip = LedStrip(config=self.config, led_count=1)
        strip._update_buffers()
        self.assertEqual([0, 0, 0, 0, 0, 0], list(strip._transmit_buffers[0]))
        strip.add_rgb(0, 1.0, 0.0, 1.0)
        strip._update_buffers()
        self.assertEqual([0, 0, 0, 0, 255, 255], list(strip._transmit_buffers[0]))

    def test_two_strips(self):
        strip = LedStrip(config=self.config, led_count=[2, 2], ip=['1', '2'])
        strip._update_buffers()
        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 0, 0], list(strip._transmit_buffers[0]))
        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 0, 0], list(strip._transmit_buffers[1]))
        strip.add_rgb(0, 1.0, 0.0, 1.0)
        strip.add_rgb(3, 0.0, 1.0, 0.0)
        strip._update_buffers()
        self.assertEqual([0, 0, 0, 0, 255, 255, 0, 0, 0], list(strip._transmit_buffers[0]))
        self.assertEqual([0, 0, 0, 0, 0, 0, 255, 0, 0], list(strip._transmit_buffers[1]))

    def test_two_strips_flipped(self):
        strip = LedStrip(config=self.config, led_count=[2, 2],
                         flip=[True, False], ip=['1', '2'])
        strip._update_buffers()
        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 0, 0], list(strip._transmit_buffers[0]))
        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 0, 0], list(strip._transmit_buffers[1]))
        strip.add_rgb(0, 1.0, 0.0, 1.0)
        strip.add_rgb(3, 0.0, 1.0, 0.0)
        strip._update_buffers()
        self.assertEqual([0, 0, 0, 0, 0, 0, 0, 255, 255], list(strip._transmit_buffers[0]))
        self.assertEqual([0, 0, 0, 0, 0, 0, 255, 0, 0], list(strip._transmit_buffers[1]))

    def test_two_strips_flipped_opc(self):
        strip = LedStrip(config=self.config, protocol=['opc', 'opc'],
                         led_count=[2, 2], flip=[True, False], ip=['1', '2'])
        strip._update_buffers()
        self.assertEqual([0, 0, 0, 2, 0, 0, 0, 0, 0, 0], list(strip._transmit_buffers[0]))
        self.assertEqual([0, 0, 0, 2, 0, 0, 0, 0, 0, 0], list(strip._transmit_buffers[1]))
        strip.add_rgb(0, 1.0, 0.0, 1.0)
        strip.add_rgb(3, 0.0, 1.0, 0.0)
        strip._update_buffers()
        self.assertEqual([0, 0, 0, 2, 0, 0, 0, 255, 0, 255], list(strip._transmit_buffers[0]))
        self.assertEqual([0, 0, 0, 2, 0, 0, 0, 0, 255, 0], list(strip._transmit_buffers[1]))



if __name__ == '__main__':
    unittest.main()
