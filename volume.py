#! /usr/bin/python
import os, sys, signal
import psutil
import subprocess

moode_vol_file = '/var/www/vol.sh'
tda7439_file = '/home/pi/bin/tda7439'
disp_mode_file = '/var/local/disp_mode'
tda7439_info_file = '/var/local/TDA7439_saved_info'
process_name = 'ssd1306_disp.py'

Normal_Vol_l = 86
Normal_Vol_h = 94

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
        if (os.path.isfile(moode_vol_file)):
            command = moode_vol_file + " up 1"
            print command
            os.system(command)
        else:
            os.system('mpc volume +1 > /dev/null 2>&1')
    else:
        if (os.path.isfile(tda7439_file)):
            command = tda7439_file + " gain up > /dev/null 2>&1"
            print command
            os.system(command)
            pid = get_pid()
            if (pid > 0): os.kill(pid, signal.SIGUSR1)

elif (sys.argv[1] == 'down'):
    if (gain > 0) and (os.path.isfile(tda7439_file)):
        command = tda7439_file + " gain down > /dev/null 2>&1"
        print command
        os.system(command)
        pid = get_pid()
        if (pid > 0): os.kill(pid, signal.SIGUSR1)
    else:
        if (os.path.isfile(moode_vol_file)):
            command = moode_vol_file + " dn 1"
            print command
            os.system(command)
        else:
            os.system('mpc volume -1 > /dev/null 2>&1')

elif (sys.argv[1] == 'normal-l'):
    if (os.path.isfile(moode_vol_file)):
        command = moode_vol_file + " " + str(Normal_Vol_l)
        print command
        os.system(command)
    else:
        command = "mpc volume " + str(Normal_Vol_l) + " > /dev/null 2>&1"
        print command
        os.system(command)
    if (os.path.isfile(tda7439_file)):
        command = tda7439_file + " gain 0 > /dev/null 2>&1"
        print command
        os.system(command)
        pid = get_pid()
        if (pid > 0): os.kill(pid, signal.SIGUSR1)

elif (sys.argv[1] == 'normal-h'):
    if (os.path.isfile(moode_vol_file)):
        command = moode_vol_file + " " + str(Normal_Vol_h)
        print command
        os.system(command)
    else:
        command = "mpc volume " + str(Normal_Vol_h) + " > /dev/null 2>&1"
        print command
        os.system(command)
    if (os.path.isfile(tda7439_file)):
        command = tda7439_file + " gain 0 > /dev/null 2>&1"
        print command
        os.system(command)
        pid = get_pid()
        if (pid > 0): os.kill(pid, signal.SIGUSR1)

