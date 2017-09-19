#!/usr/bin/env python
# coding: utf-8

from distutils.core import setup

setup(
	name='Distutils',
	version='1.0',
	description='Python interface for streaming color information to a WS2812 LED strip connected to an ESP8266 running the firmware from https://github.com/cnlohr/esp8266ws2812i2s',
	author='Michael Cipold',
	author_email='github@cipold.de',
	url='https://github.com/cipold/pyledstrip',
	py_modules=['pyledstrip'],
)
