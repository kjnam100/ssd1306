#! /usr/bin/python
# coding=utf-8
import os, sys
import subprocess
import urlparse

inet_radio_stat_file = "/var/local/inet_radio_stat"
inet_radio_station_file = "/var/local/inet_radio_station"
inet_radio_mesg_file = "/var/local/ramdisk/inet_radio_mesg"

ssd1306_disp_mode_file = "/home/pi/bin/ssd1306_disp_mode.py"
#mpayerCommand = "mplayer --novideo -noconsolecontrols -ao alsa:device=hw "
mpayerCommand = "mplayer --novideo --cache=192 -noconsolecontrols -ao alsa:device=hw "

#=====================================================================

def main():
    station = []

    try:
        with open(inet_radio_station_file, 'r') as fd:
            info = fd.read().splitlines()
    except IOError:
        sys.exit()

    for item in info:
        url_info = urlparse.urlparse(item)
        if (url_info.scheme):
            station.append(item.split(None, 1))

    station_num = len(station)

    file_sn = -1;
    try:
        with open(inet_radio_stat_file, 'r') as fd:
            file_sn = sn = int(fd.read().splitlines()[0])
    except:
        sn = 0

    if (len(sys.argv) > 1): 
        if (sys.argv[1] == "up"):
            sn = (sn + 1) % station_num
        elif (sys.argv[1] == "down"):
            sn = (sn - 1) % station_num
        else:
            sn = int(sys.argv[1]) % station_num
        #print sn
    
    cur_command = subprocess.check_output('ps -eo args | grep mplayer', shell=True).splitlines()[0]
    command = mpayerCommand + station[sn][0]

    if (command != cur_command):
        # 이전 mpayer kill
        os.system("killall mplayer > /dev/null 2>&1")

        # mplayer 실행
        #command += " > /dev/null 2>&1 &"
        command += " 2> /dev/null " + ">" + inet_radio_mesg_file + "&"
        os.system(command)

    # Inet Radio display 모드
    #command = ssd1306_disp_mode_file + " inet_radio"
    #os.system(command)

    if (sn != file_sn):
        try:
            with open(inet_radio_stat_file, 'w') as fd:
                fd.write(str(sn))
        except IOError:
            sys.exit()


if __name__ == "__main__":
    main()

