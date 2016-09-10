#! /usr/bin/python
import os, sys, signal
import psutil
import subprocess

process_name = 'ssd1306_disp.py'

def get_pid():
    for proc in psutil.process_iter():
        if (proc.name() == process_name):
            return proc.pid

    return 0

#=================================================

pid = get_pid()
if (pid > 0): os.kill(pid, signal.SIGUSR1)

