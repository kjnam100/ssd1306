#! /usr/bin/python
# coding=utf-8

import RPi.GPIO as GPIO
import time
import os
import sys

LED_RED_PIN = 6
LED_GREEN_PIN = 12
LED_BLUE_PIN = 13

BLINK_DELAY = 0.05 

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_RED_PIN, GPIO.OUT)
GPIO.setup(LED_GREEN_PIN, GPIO.OUT)
GPIO.setup(LED_BLUE_PIN, GPIO.OUT)

color_code = {
    "red"       : [1, 0, 0],
    "green"     : [0, 1, 0],
    "blue"      : [0, 0, 1],
    "yellow"    : [1, 1, 0],
    "magenta"   : [1, 0, 1],
    "cyan"      : [0, 1, 1],
    "white"     : [1, 1, 1],
    "black"     : [0, 0, 0],
    "off"       : [0, 0, 0]
}

def activate_led(color):
    GPIO.output(LED_RED_PIN, color_code[color][0])
    GPIO.output(LED_GREEN_PIN, color_code[color][1])
    GPIO.output(LED_BLUE_PIN, color_code[color][2])

def addblink(color, onoff):
    if (color_code[color][0] == 1):
        GPIO.output(LED_RED_PIN, onoff)
    if (color_code[color][1] == 1):
        GPIO.output(LED_GREEN_PIN, onoff)
    if (color_code[color][2] == 1):
        GPIO.output(LED_BLUE_PIN, onoff)

def usage():
    sys.stderr.write("Usage: " + os.path.basename(sys.argv[0]) + " red|green|blue|yellow|magenta|cyan|white|black [addblink|blink]\n")
    sys.exit()

if (len(sys.argv) < 2):
    usage()

led_color = sys.argv[1]
if sys.argv[1] in color_code:
    if (len(sys.argv) < 3):
        activate_led(led_color)
    else: 
        o_red = GPIO.input(LED_RED_PIN)
        o_green = GPIO.input(LED_GREEN_PIN)
        o_blue = GPIO.input(LED_BLUE_PIN)

        if (sys.argv[2] ==  'addblink'):
            addblink(sys.argv[1], 1)    # on
            time.sleep(BLINK_DELAY)
            addblink(sys.argv[1], 0)    # off
            time.sleep(BLINK_DELAY)
            addblink(sys.argv[1], 1)    # on
            time.sleep(BLINK_DELAY)
            addblink(sys.argv[1], 0)    # off
            time.sleep(BLINK_DELAY)

        elif (sys.argv[2] ==  'blink'):
            activate_led(led_color)    # on
            time.sleep(BLINK_DELAY)
            activate_led('black')      # off
            time.sleep(BLINK_DELAY)
            activate_led(led_color)    # on
            time.sleep(BLINK_DELAY)
            activate_led('black')      # off
            time.sleep(BLINK_DELAY)
        else:
            usage()

        GPIO.output(LED_RED_PIN, o_red)
        GPIO.output(LED_GREEN_PIN, o_green)
        GPIO.output(LED_BLUE_PIN, o_blue)
else:
    usage()

