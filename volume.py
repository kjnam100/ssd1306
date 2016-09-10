#! /usr/bin/python
import os, sys, signal
import psutil
import subprocess

disp_mode_file = '/var/local/disp_mode'
tda7439_info_file = '/var/local/TDA7439_saved_info'
process_name = 'ssd1306_disp.py'

def get_tda7439_gain():
    try:
        with open(tda7439_info_file, 'r') as fd:
            return int(fd.read().splitlines()[4])
    except:
        return 0

def get_pid():
    for proc in psutil.process_iter():
        #print(proc.name(), proc.pid)
        if (proc.name() == process_name):
            return proc.pid

    return 0

#=================================================

if (len(sys.argv) < 2):
    sys.exit(0)

vol = subprocess.check_output('mpc volume', shell=True).splitlines()[0]
vol = vol.split(':')[1]
vol = int(vol.split('%')[0])

gain = get_tda7439_gain()

if (sys.argv[1] == 'up'):
    if (vol < 100):
        #os.system('mpc volume +1 > /dev/null 2>&1')
        os.system('/var/www/vol.sh up 1')
    else:
        os.system('/home/pi/bin/tda7439 gain up > /dev/null 2>&1')
        pid = get_pid()
        if (pid > 0): os.kill(pid, signal.SIGUSR1)

elif (sys.argv[1] == 'down'):
    if (gain > 0):
        os.system('/home/pi/bin/tda7439 gain down > /dev/null 2>&1')
        pid = get_pid()
        if (pid > 0): os.kill(pid, signal.SIGUSR1)
    else:
        #os.system('mpc volume -1 > /dev/null 2>&1')
        os.system('/var/www/vol.sh dn 1')

elif (sys.argv[1] == 'normal-l'):
    os.system('/var/www/vol.sh 86')
    os.system('/home/pi/bin/tda7439 gain 0 > /dev/null 2>&1')
    pid = get_pid()
    if (pid > 0): os.kill(pid, signal.SIGUSR1)

elif (sys.argv[1] == 'normal-h'):
    os.system('/var/www/vol.sh 94')
    os.system('/home/pi/bin/tda7439 gain 0 > /dev/null 2>&1')
    pid = get_pid()
    if (pid > 0): os.kill(pid, signal.SIGUSR1)

'''
try:
    with open(disp_mode_file, 'r') as fd:
        disp_mode = fd.read().splitlines()[0]
        if (disp_mode == 'mpd'):
            pass
except IOError:
    pass
'''
