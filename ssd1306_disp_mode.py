#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2016 Nam, Kookjin - All Rights Reserved.
"""

import os, sys, signal
import psutil

process_name = 'ssd1306_disp.py'
disp_mode_file = '/var/local/disp_mode'

def get_pid():
    for proc in psutil.process_iter():
        #print(proc.name(), proc.pid)
        if (proc.name() == process_name):
            return proc.pid

    return 0

if (len(sys.argv) < 2):
    sys.exit()

try:
    with open(disp_mode_file, 'w') as fd:
        fd.write(sys.argv[1])
except IOError:
    print("io error")
    sys.exit()

pid = get_pid()
if (pid > 0): os.kill(pid, signal.SIGUSR1)
