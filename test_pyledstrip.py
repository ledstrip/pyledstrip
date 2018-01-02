#!/usr/bin/env python
# coding: utf-8

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
		strip = LedStrip(led_count=[321, 1337], ip=['123.123.123.123', '1.1.1.1'], port=[54321, 12345], flip=[True, False])
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
		self.assertEqual([54321,], strip._ports)
		self.assertEqual([True,], strip._flips)


if __name__ == '__main__':
	unittest.main()
