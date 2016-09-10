#! /usr/bin/python
# -*- coding: utf-8 -*- 
import time

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

import Image
import ImageDraw
import ImageFont

import datetime
import sys
import signal

from math import ceil
from time import sleep

reload(sys)
sys.setdefaultencoding('utf-8')

# Raspberry Pi pin configuration:
RST = 24

# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0

# 128x64 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

# Load default font.
font_mesg = ImageFont.truetype('/home/pi/fonts/NGULIM.TTF', 16)

#--------------------------------------------------------------------------------------------

def main():
    # Initialize library.
    disp.begin()

    # Clear display.
    # disp.clear()
    # disp.display()

    # Create blank image for drawing.
    # Make sure to create image with mode '1' for 1-bit color.
    width = disp.width
    height = disp.height
    image = Image.new('1', (width, height))

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    if (len(sys.argv) < 2):
        mesg = "Hello World!"
    else:
        mesg = sys.argv[1]

    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    draw.text((0, 0), unicode(mesg), font=font_mesg, fill=255)
    disp.image(image)
    disp.display()


if __name__ == "__main__":
    try:
        main()

    # Catch all other non-exit errors
    except Exception as e:
        sys.stderr.write("Unexpected exception: %s" % e)
        sys.exit(1)

    # Catch the remaining exit errors
    except:
        sys.exit(0)


