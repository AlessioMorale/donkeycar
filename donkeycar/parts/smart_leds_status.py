import usb.core
import usb.control
import time

# The following LittleWire code taken from https://github.com/mottop/VeryLittleWire 
# a fork of https://github.com/adajoh99/VeryLittleWire
#
# Following the original Copyright notice for the library 
#
# File: littleWire.py
# Version: v1.0
# Purpose: Provides a Python interface to the Little Wire USB Multi-Tool
#          developed by Ihsan Kehribar
# Author: Adam Johnson
# Copyright 2012 by Adam Johnson <apjohnson@gmail.com>
#
# This file is a direct Python translation of the C++ library by Ihsan Kehribar
# <ihsan@kehribar.me> and Omer Kilic <omerkilic@gmail.com>, version 0.9.
# It is released under the following license, the same as the original C++ source.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

#USB constants
VENDOR_ID = 0x1781
PRODUCT_ID = 0x0C9F
USB_TIMEOUT = 1
RX_BUFFER_SIZE = 64
# Minumum interval between updates
# If you see something like 'WARN Event TRB for slot 3 ep 0 with no TDs queued?'
# in your kernel.log then try to slightly raise this value
MIN_UPDATE_INTERVAL = 0.001

# Code ------------------------------------------------------------------------

class device:
    """ Class to control a LittleWire USB Multi-Tool."""
    lw = None

    def __init__(self):
        """Finds the first littleWire and attaches to it"""
        self.lw = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        
        if self.lw == None:
            raise ValueError('Device not Found!')
        try:
            self.lw.set_configuration()
        except:
            # most of the times reset recover the device from some inconsistent state
            self.lw.reset()
            time.sleep(1)
            self.lw.set_configuration()
        
    def readFirmwareVersion(self):
        """Returns littleWire firmware version"""
        rtn = self.lw.ctrl_transfer(bmRequestType=0xC0, bRequest=34, wValue=0, wIndex=0, data_or_wLength=8, timeout=USB_TIMEOUT)
        version = rtn.pop()
        return str((version & 0xF0) >> 4 )+"." + str((version & 0x0F))

# Note: all non needed functionalities from the original lib are removed, only init/and ws28xx left

    def ws2812_write(self, pin, r, g, b):
        self.lw.ctrl_transfer(bmRequestType=0xC0, bRequest=54, wValue=int((g<<8) | pin | 0x30), wIndex=(int(b<<8) | r), data_or_wLength=8, timeout=USB_TIMEOUT)
    
    def ws2812_flush(self, pin):
        self.lw.ctrl_transfer(bmRequestType=0xC0, bRequest=54, wValue=int( pin | 0x10), wIndex=0, data_or_wLength=8, timeout=USB_TIMEOUT)

    def ws2812_preload(self, r, g, b):
        self.lw.ctrl_transfer(bmRequestType=0xC0, bRequest=54, wValue=int((g<<8) | 0x20), wIndex=(int(b<<8) | r), data_or_wLength=8, timeout=USB_TIMEOUT)
#  End if LittleWire interface


class SMART_LEDS:
    ''' 
    Toggle a GPIO pin on at max_duty pwm if condition is true, off if condition is false.
    Good for LED pwm modulated
    '''
    def __init__(self, stringlen, pin):
        self.last_execution = time.time()
        self.lw = device()
        self.blink_changed = 0
        self.on = False
        self.running = True
        self.force_off = False

        self.pin = pin
        self.stringlen = stringlen
        print('lw detected, fw:', self.lw.readFirmwareVersion())
        self.ledstatus = []
        for i in range(self.stringlen):
            color = (128,128,128)
            self.ledstatus.append(color)
        self.update_leds()        

    def toggle(self, condition):
        self.force_off = not condition

    def update_leds(self, zero=False):
        try:
            ledcopy = self.ledstatus
            #ensure the attiny has finished processing the last update
            remaining =  MIN_UPDATE_INTERVAL - (time.time() - self.last_execution)
            if(remaining > 0):
                time.sleep(remaining)
            for color in ledcopy:
                if zero:
                    self.on = False
                    self.lw.ws2812_preload(0, 0, 0)
                else:
                    self.on = True
                    self.lw.ws2812_preload(color[0], color[1], color[2])
            self.lw.ws2812_flush(self.pin)
        except usb.core.USBError:
            pass
        self.last_execution = time.time()

    def blink(self, rate):
        if time.time() - self.blink_changed > rate:
            self.toggle(not self.on)
            self.blink_changed = time.time()

    def run(self):
        if not self.on:
            self.on = True

    def run_threaded(self, blink_rate):
        if blink_rate == 0:
            self.toggle(False)
        elif blink_rate > 0:
            self.blink(blink_rate)
        else:
            self.toggle(True)

    def update(self):
        while(self.running):
            self.update_leds(self.force_off)
            time.sleep(0.05)

    def set_rgb(self, r, g, b):
        color = [r, g, b]
        color = [max(min( int(x * 255.0/100.0), 255), 0) for x in color]
        for i in range(self.stringlen):
            self.ledstatus[i] = color
    
    def shutdown(self):
        self.toggle(False)
        self.running = False


if __name__ == "__main__":
    import time
    import sys

    p = SMART_LEDS(4, 1)
    rate = 0.5
    iter = 0
    while iter < 50:
        p.run(rate)
        time.sleep(0.1)
        iter += 1
    
    delay = 0.1

    iter = 0
    while iter < 100:
        p.set_rgb(iter, 100-iter, 0)
        time.sleep(delay)
        iter += 1
    
    iter = 0
    while iter < 100:
        p.set_rgb(100 - iter, 0, iter)
        time.sleep(delay)
        iter += 1

    p.shutdown()

