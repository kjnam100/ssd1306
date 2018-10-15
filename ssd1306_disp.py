#! /usr/bin/python
#-*- coding: utf-8 -*- 

"""
Copyright (c) 2016 Nam, Kookjin - All Rights Reserved.
Do not distribute modified versions of this file.
Non-commercial use only. You may not use this work for commercial purposes.
Any question: http://blog.naver.com/kjnam100/220805352857 
"""

import time

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import datetime
import os, sys, subprocess
import signal
import json

import requests

from math import ceil
from time import sleep
from mpd import MPDClient, MPDError, CommandError

import urlparse

reload(sys)
sys.setdefaultencoding('utf-8')

# Raspberry Pi pin configuration:
RST = 24

# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0

# Load default font.
font_gulim11 = ImageFont.truetype('/home/pi/fonts/NGULIM.TTF', 11)
font_gulim12 = ImageFont.truetype('/home/pi/fonts/NGULIM.TTF', 12)
font_gulim13 = ImageFont.truetype('/home/pi/fonts/NGULIM.TTF', 13)
font_gulim14 = ImageFont.truetype('/home/pi/fonts/NGULIM.TTF', 14)
font_gulim15 = ImageFont.truetype('/home/pi/fonts/NGULIM.TTF', 15)
font_gulim16 = ImageFont.truetype('/home/pi/fonts/NGULIM.TTF', 16)
font_gulim20 = ImageFont.truetype('/home/pi/fonts/NGULIM.TTF', 20)
font_minecraftia12 = ImageFont.truetype('/home/pi/fonts/Minecraftia-Regular.ttf', 12)
font_minecraftia14 = ImageFont.truetype('/home/pi/fonts/Minecraftia-Regular.ttf', 14)
font_minecraftia20 = ImageFont.truetype('/home/pi/fonts/Minecraftia-Regular.ttf', 20)

disp_mode = 'clock' 
disp_mode_file = '/var/local/disp_mode'
tda7439_info_file = '/var/local/TDA7439_saved_info'
inet_radio_stat_file = "/var/local/inet_radio_stat"
inet_radio_station_file = "/var/local/inet_radio_station"
inet_radio_mesg_file = "/var/local/ramdisk/inet_radio_mesg"
TDA7439_SAVED_INFO = "/var/local/TDA7439_saved_info"
moode_airplay_file = "/var/www/spscache.json"

# 기상청 날씨 API 관련
apikey = 'IzVFRF6gbi8IHnpNweJbBF547ybv9GAWm8e9TNSvhD%2BXQyNWZiJcBgiJe%2F2cmAEc2uKyYYq7SL3iO5obSx1Krg%3D%3D'
apinxy_json = '&nx=62&ny=123&_type=json' # 성남 분당구 삼평동
#apinxy_json = '&nx=61&ny=125&_type=json' # 서울 강남구 역삼1동
#apinxy_json = '&nx=60&ny=127&_type=json' # 서울 종로구

#---------------------------------------------------------------------

def my_unicode(mesg, errors='ignore'):
    try:
        return unicode(mesg, errors=errors)
    except:
        return mesg

#---------------------------------------------------------------------

def make_stream_info_mesg(stats):
    album = ""
    bps = 0
    if 'bitrate' in stats: 
        # VBS의 경우 bps 정보의 자릿수가 변경됨에 따른 디스플레이 흔들림 방지를 위해...
        bps = int(stats['bitrate'])
        album += stats['bitrate'] + " kbps"
    if 'audio' in stats:
        mesg = stats['audio'].split(':')[0]
        q, r = divmod(int(mesg), 1000)
        if (r == 0): mesg = str(q) + " ㎑"
        else: mesg = str(float(mesg) / 1000) + " ㎑"
        if (bps < 500): # 500은 대강 정한 값. VBR의 경우 1000kbps를 넘을 가능성 고려해서
            album += " "
        album += " " + mesg
        if (bps < 500): # 500은 대강 정한 값. VBR의 경우 1000kbps를 넘을 가능성 고려해서
            album += " "
        album += " " + stats['audio'].split(':')[1] + ":" + stats['audio'].split(':')[2]

    return album

#----------------------------------------------------------------------

prev_moode_airplay_file_mtime = 0
airplay_meta_data = {}
showStreamInfo = False

class PollerError(Exception):
    """Fatal error in poller."""


class MPDPoller(object):
    def __init__(self, host="localhost", port="6600", password=None):
        self._host = host
        self._port = port
        self._password = password
        self._client = MPDClient()

    def connect(self):
        try:
            self._client.connect(self._host, self._port)
        # Catch socket errors
        except IOError as err:
            errno, strerror = err
            #print("Could not connect to '%s': %s" % (self._host, strerror))
            return -1
            #raise PollerError("Could not connect to '%s': %s" %
            #                  (self._host, strerror))

        # Catch all other possible errors
        # ConnectionError and ProtocolError are always fatal.  Others may not
        # be, but we don't know how to handle them here, so treat them as if
        # they are instead of ignoring them.
        except MPDError as e:
            #raise PollerError("Could not connect to '%s': %s" %
            #                  (self._host, e))
            return -1

        if self._password:
            try:
                self._client.password(self._password)

            # Catch errors with the password command (e.g., wrong password)
            except CommandError as e:
                raise PollerError("Could not connect to '%s': "
                                  "password commmand failed: %s" %
                                  (self._host, e))

            # Catch all other possible errors
            except (MPDError, IOError) as e:
                raise PollerError("Could not connect to '%s': "
                                  "error with password command: %s" %
                                  (self._host, e))
        return 0

    def disconnect(self):
        # Try to tell MPD we're closing the connection first
        try:
            self._client.close()

        # If that fails, don't worry, just ignore it and disconnect
        except (MPDError, IOError):
            pass

        try:
            self._client.disconnect()

        # Disconnecting failed, so use a new client object instead
        # This should never happen.  If it does, something is seriously broken,
        # and the client object shouldn't be trusted to be re-used.
        except (MPDError, IOError):
            self._client = MPDClient()

    def poll(self):
        global my_network
        global prev_moode_airplay_file_mtime
        global airplay_meta_data
        global showStreamInfo

        play_time = [0, 0]
        mode = 0

        # Airplay, moode_airplay_file modify time이 변경되었는지 체크
        if (os.path.isfile(moode_airplay_file) and os.path.getsize(moode_airplay_file) > 0):
            moode_airplay_file_mtime = os.path.getmtime(moode_airplay_file)
            if (moode_airplay_file_mtime == prev_moode_airplay_file_mtime and airplay_meta_data):
                return(airplay_meta_data)

            prev_moode_airplay_file_mtime = moode_airplay_file_mtime

            # Airplay, moode_airplay_file이 제대로 해석되면 airplay로 간주함
            try:
                with open(moode_airplay_file, 'r') as fd:
                    info = fd.read()
                    jinfo = json.loads(info)
                    if (jinfo['state'] == 'ok' and jinfo['progress'] != None):
                        try: album = jinfo['album']
                        except: album = ""
                        if (album == None): album = ""

                        try: artist = jinfo['artist']
                        except: artist = ""
                        if (artist == None): artist = ""

                        try: title = jinfo['title']
                        except: title = ""
                        if (title == None): title = ""

                        try:
                            # The volume is sent as a string -- airplay_volume,volume,lowest_volume,highest_volume
                            # where "volume", "lowest_volume" and "highest_volume" are given in dB.
                            # The "airplay_volume" is what's sent by the source (e.g. iTunes) to the player,
                            # and is from 0.00 down to -30.00, with -144.00 meaning "mute". This is linear on the
                            # volume control slider of iTunes or iOS AirPlay
                            vol = (float(jinfo['volume'][1]) - float(jinfo['volume'][2])) / \
                                  (float(jinfo['volume'][3]) - float(jinfo['volume'][2]))
                            vol = int(round(vol * 100))
                        except: vol = None

                        airplay_meta_data = {'mode':mode, 'album':album, 'title':title, 'artist':artist,
                            'state':'airplay', 'eltime':0, 'play_time':play_time,
                            'random':0, 'repeat':0, 'volume':vol}
                        return(airplay_meta_data)
            except: pass
        # End of Airplay

        try:
            song = self._client.currentsong()
            stats = self._client.status()

            # sometimes song['artist'] type is list, so make it string
            artist = ""
            if 'artist' in song: 
                if type(song['artist']) is list:
                    artist += song['artist'][0]
                    slen = len(song['artist'])
                    for i in range(1,slen):
                        artist += "; " + song['artist'][i]
                else: artist += song['artist']

            state = stats['state']

            # Radio stream 인지 체크
            if 'file' in song and \
                (not song['file'].startswith(my_network)) and \
                (song['file'].startswith('http://') or song['file'].startswith('https://') or song['file'].startswith('mms://')):
                mode |= 0x01 # Radio Stream 
                if 'name' in song: title = song['name']
                else: title = "Radio Stream"

                if 'title' in song:
                    if artist: artist += " - "
                    artist += song['title']
                if not artist: artist = song['file']

                album = make_stream_info_mesg(stats)

            # Radio stream이 아니면...
            else:
                if 'file' in song and song['file'].startswith(my_network):
                    mode |= 0x02 # means DLNA

                if 'album' not in song or (showStreamInfo and state != 'stop'): 
                    album = make_stream_info_mesg(stats)
                    mode |= 0x01 # means 앨범정보 대신 stream 정보
                else: album = song['album']
            
                if 'title' not in song: 
                    if 'file' in song: title = song['file']
                    elif 'error' in stats: title = stats['error']
                    else: title = ""
                else: title = song['title']

            try: songplayed = stats['elapsed']
            except: songplayed = '0'
            random = stats['random']
            repeat = stats['repeat']
            vol = stats['volume']
            m, s = divmod(float(songplayed), 60)
            h, m = divmod(m, 60)
            eltime = h * 3600 + m * 60 + s
            try:
                time_str = stats['time'].split(':')
                play_time[0] = int(time_str[0])
                play_time[1] = int(time_str[1])
            except:
                pass

            return({'mode':mode, 'album':album, 'title':title, 'artist':artist,
                'state':state, 'eltime':eltime, 'play_time':play_time,
                'random':random, 'repeat':repeat, 'volume':int(vol)})

        # Couldn't get the current song, so try reconnecting and retrying
        except (MPDError, IOError):
            # No error handling required here
            # Our disconnect function catches all exceptions, and therefore
            # should never raise any.
            self.disconnect()

            try:
                self.connect()

            # Reconnecting failed
            except PollerError as e:
                raise PollerError("Reconnecting failed: %s" % e)

            return None

#--------------------------------------------------------------------------------------------

def get_disp_mode():
    global disp_mode
    global px1, px2, px3
    global wpx1, wpx2, wpx3
    global radio_station, total_radio_station_num, radio_station_num

    # get display 모드
    try:
        with open(disp_mode_file, 'r') as fd:
            disp_mode = fd.read().splitlines()[0]
            if (disp_mode == 'mpd'):
                px1 = px2 = px3 = 0
                wpx1 = wpx2 = wpx3 = 0 
    except IOError:
        disp_mode = 'clock'

    # FM station 번호 가져오기
    if (disp_mode == "inet_radio" or disp_mode == "auto"):
        try:
            with open(inet_radio_stat_file, 'r') as fd:
                radio_station_num = int(fd.read().splitlines()[0])
        except:
            radio_station_num = 0

        # FM station 번호의 station 이름 가져오기
        # station = []
        radio_station = "" # defaut name
        try:
            with open(inet_radio_station_file, 'r') as fd:
                info = fd.read().splitlines()
                i = 0
                for item in info:
                    url_info = urlparse.urlparse(item)
                    if (url_info.scheme):
                        if (i == radio_station_num): 
                            station_info = item.split(None, 1)
                            if (len(station_info) > 1):
                                radio_station = station_info[1]
                        i += 1
                        #station.append(item.split(None, 1))
                total_radio_station_num = i
        except IOError:
            total_radio_station_num = -1
            radio_station = str(radio_station_num+1)

#
# signal hander
#
#----------------------------------------------------------------------------------------

def sig_handler(signum, frame):
    get_disp_mode()
    get_tda7439()

#----------------------------------------------------------------------------------------

urlBase = 'http://newsky2.kma.go.kr/service/SecndSrtpdFrcstInfoService2/'

weatherCur = {} # 현재온도, 현재습도, 현재하늘상태, 강수형태, 예상온도, 비올확률
weatherCurTime = None
timeReqCur = None
minutes_10 = datetime.timedelta(minutes=10)

weatherSKY = ['', '맑음', "구름조금", "구름많음", "흐림"] # 현재하늘상태
#weatherSKY = ['', '맑음', "흐림 약", "흐림 중", "흐림 강"] # 현재하늘상태
weatherPTY = ['없음', "비", "비/눈", "눈"]                 # 현재강우상태

#
# 날씨 실황 조회
#
#----------------------------------------------------------------------------------------
def getWeatherCur(rtime):
    global weatherCurTime
    global weatherCur
    global timeReqCur

    wtime = rtime - datetime.timedelta(minutes=rtime.minute) 

    # 1분에 한번이상 진행 안함.
    # 현재 가용한 데이터가 없으면 진행함.
    # 요청한 시간의 데이터가 현재 수집된 데이터의 시간과 같지않고, 현시간이 ?9분이면 진행함.
    # 보통 정시에 데이터 요구하면 수신되는 데이터 없음.
    if (timeReqCur == rtime) or \
       (weatherCurTime and ((wtime == weatherCurTime) or \
            (timeReqCur and abs(rtime - timeReqCur) < minutes_10 and (rtime.minute % 10) != 9))): 
        return

    timeReqCur = rtime

    apiymd = str(wtime.year) + str('%02d' % wtime.month)  + str('%02d' % wtime.day)
    apihour = str('%02d' % wtime.hour) + '00'

    url = urlBase + 'ForecastGrib' + '?ServiceKey=' + apikey + \
          '&base_date=' + apiymd + '&base_time=' + apihour + apinxy_json
    #print("Cur request", apiymd, apihour, rtime.minute)

    try:
        r = requests.get(url)
        if (r.status_code != requests.codes.ok): return # http error

        weatherCur['resultCode'] = int(r.json()['response']['header']['resultCode'])
        if (weatherCur['resultCode'] != 0): 
            sys.stderr.write("Weather forecast Response: %s\n" % r.json()['response']['header']['resultMsg'])
            return  # 응답 오류

        # 응답 데이터 기록
        temp = {}
        try:
            for data in r.json()['response']['body']['items']['item']:
                temp[data['category']] = data['obsrValue']
        except: pass

        # 응답에 유효한 데이터가 없으면...
        if not temp:
            #print("Cur", r.text)
            #print("Cur empty response")
            localtime = time.localtime(time.time())
            now = datetime.datetime(localtime.tm_year, localtime.tm_mon, localtime.tm_mday, localtime.tm_hour, localtime.tm_min)
            if (weatherCurTime == None) or ((now - weatherCurTime).seconds // 3600 > 2):    # 현재 가용한 데이터가 없으면, 1시간전 데이터라도 가져옴
                if (now - wtime).seconds / 3600 < 1:
                    getWeatherCur(rtime - datetime.timedelta(hours=1))
                timeReqCur = rtime
                return

        if temp:
            weatherCur = temp
            weatherCur['resultCode'] = int(r.json()['response']['header']['resultCode'])
            weatherCurTime = wtime

    except Exception as e:
        sys.stderr.write("getWeatherCur() exception: %s" % e)
        return

#----------------------------------------------------------------------

weatherFore = {} 
weatherForeTime = None
timeReqFore = None

#
# 날씨 단기예보 조회
#
#----------------------------------------------------------------------
def getWeatherFore(rtime):
    global weatherForeTime
    global weatherFore
    global timeReqFore

    # 유효 단기예보 시간: 2, 5, 8, 11, 14, 17, 20, 23
    wtime = rtime - datetime.timedelta(hours=(rtime.hour + 1) % 3, minutes=rtime.minute) # 

    # 1분에 한번이상 진행 안함.
    # 현재 가용한 데이터가 없으면 진행함.
    # 요청한 시간의 데이터가 현재 수집된 데이터의 시간과 같지않고, 현시간이 ?9분이면 진행함.
    # 보통 정시에 데이터 요구하면 수신되는 데이터 없음.
    if (timeReqFore == rtime) or \
       (weatherForeTime and ((wtime == weatherForeTime) or \
            (timeReqFore and abs(rtime - timeReqFore) < minutes_10 and (rtime.minute % 10) != 9))): 
        return

    timeReqFore = rtime

    apiymd = str(wtime.year) + str('%02d' % wtime.month)  + str('%02d' % wtime.day)
    apihour = str('%02d' % wtime.hour) + '00'

    url = urlBase + 'ForecastSpaceData' + '?ServiceKey=' + apikey + \
          '&base_date=' + apiymd + '&base_time=' + apihour + apinxy_json
    #print("Fore request", apiymd, apihour, rtime.minute)

    try:
        r = requests.get(url)
        if (r.status_code != requests.codes.ok): return # http error

        weatherFore['resultCode'] = int(r.json()['response']['header']['resultCode'])
        if (weatherFore['resultCode'] != 0): 
            sys.stderr.write("Weather forecast Response: %s\n" % r.json()['response']['header']['resultMsg'])
            return  # 응답 오류

        # 응답 데이터 기록
        temp = {}
        try:
            for data in  r.json()['response']['body']['items']['item']:
                temp[data['category']] = data['fcstValue']
        except: pass

        # 응답에 유효한 데이터가 없으면...
        if not temp:
            #print("Fore", r.text)
            #print("Fore empty response")
            localtime = time.localtime(time.time())
            now = datetime.datetime(localtime.tm_year, localtime.tm_mon, localtime.tm_mday, localtime.tm_hour, localtime.tm_min)
            if (weatherForeTime == None) or ((now - weatherForeTime).seconds // 3600 > 3):    # 현재 가용한 데이터가 없으면, 3시간전 데이터라도 가져옴
                if (now - wtime).seconds / 3600 < 3:
                    getWeatherFore(rtime - datetime.timedelta(hours=3))
                timeReqFore = rtime
                return

        if temp:
            weatherFore = temp
            weatherFore['resultCode'] = int(r.json()['response']['header']['resultCode'])
            weatherForeTime = wtime

    except Exception as e:
        return

#----------------------------------------------------------------------

def weather_disp(now):
    global weatherCurTime, weatherForeTime
    global weatherCur, weatherFore

    if (weatherCurTime == None) or ((now - weatherCurTime).seconds // 3600 > 2):
        weather_str = "날씨정보 오류"
        if 'resultCode' in weatherCur.keys():
            weather_str += ": " + str(weatherCur['resultCode'])
        draw.text((0, 0), unicode(weather_str), font=font_gulim15, fill=255)
        weatherCurTime = None
        return

    old_data = False
    if (weatherCurTime and ((now - weatherCurTime).seconds // 3600 > 1)):
        old_data = True
        weatherCurTime = None
    if (weatherForeTime and ((now - weatherForeTime).seconds // 3600 > 3)):
        old_data = True
        weatherForeTime = None
                
    # 현재 날씨 
    t_str = r_str = tpm = rpm = ""
    try:
        # 온도
        if 'T3H' in weatherFore.keys():
            if (weatherFore['T3H'] > weatherCur['T1H']):
                tpm = '△' #'↑'
            elif (weatherFore['T3H'] < weatherCur['T1H']):
                tpm = '▼' #'↓'
        else: weatherForeTime = None   # 다음번에 다시 시도하도록 함
        t_str = str(int(round(weatherCur['T1H'])))             # 현재온도

        # 습도
        if 'REH' in weatherFore.keys():
            if (weatherFore['REH'] > weatherCur['REH']):
                rpm = '△' #'↑'
            elif (weatherFore['REH'] < weatherCur['REH']):
                rpm = '▼' #'↓'
        else: weatherForeTime = None   # 다음번에 다시 시도하도록 함
        r_str = str(int(round(weatherCur['REH'])))             # 현재습도
    except: 
        weatherCurTime = None  # 다음번에 다시 시도하도록 함

    # 돈도 습도 나타내기
    slen = draw.textsize(unicode(t_str + '℃ ' + r_str + '%'), font=font_gulim15)
    if (slen[0] > 77): 
        font = font_gulim13
    else: font = font_gulim15
    px = width - 10
    draw.text((px, 2), unicode('%'), font=font_gulim12, fill=255)
    slen = draw.textsize(unicode(r_str), font=font)
    px -= slen[0] + 1
    draw.text((px, 0), unicode(r_str), font=font, fill=255)
    px -= 10 
    if (rpm == '△'): py = 4
    else: py = 1
    draw.text((px, py), unicode(rpm), font=font_gulim11, fill=255)

    px -= 17
    draw.text((px, 0), unicode('℃'), font=font_gulim12, fill=255)
    slen = draw.textsize(unicode(t_str), font=font)
    px -= slen[0]
    draw.text((px, 0), unicode(t_str), font=font, fill=255)
    px -= 10 
    if (tpm == '△'): py = 4
    else: py = 1
    draw.text((px, py), unicode(tpm), font=font_gulim11, fill=255)

    # 예보 날씨 (강수확률)
    try:
        weather_str = str(int(round(weatherFore['POP']))) + '%' 
        if (old_data): weather_str = '≠' + weather_str # ≠
    except: 
        if 'resultCode' in weatherFore.keys():
            weather_str += "E: " + str(weatherFore['resultCode'])
        else: weather_str = "오류"
        weatherForeTime = None   # 다음번에 다시 시도하도록 함
    draw.text((0, 0), unicode(weather_str), font=font_gulim15, fill=255)

    # 하늘 상태 또는 강수형태
    try:
        if ('PTY' in weatherCur.keys()) and (weatherCur['PTY'] > 0):    # 유효한 강수형태인지 체크
            weather_str = weatherPTY[weatherCur['PTY']] 
        elif ('SKY' in weatherCur.keys()): 
            weather_str = weatherSKY[weatherCur['SKY']]
        elif ('SKYi' in weatherFore.keys()):
            weatherCur['SKY'] = weatherFore['SKY']
            weather_str = weatherSKY[weatherCur['SKY']]
        else:
            weatherCur['SKY'] = 0
            weather_str = weatherSKY[weatherCur['SKY']]

        if ('SKY' in weatherFore.keys()) and (weatherFore['SKY'] > 0):
            if (weatherCur['SKY'] < weatherFore['SKY']):
                weather_str += '▼' #'↓'
            elif (weatherCur['SKY'] > weatherFore['SKY']):
                weather_str += '△' #'↑'
        #else: weatherForeTime = None    # 다음번에 다시 시도하도록 함
        if ('LGT' in weatherCur.keys()) and (weatherCur['LGT'] > 0):    # 낙뢰
            weather_str += ' и'
        else: weather_str += ' '
        if ('WSD' in weatherCur.keys()):    # 풍속
            weather_str += " ≈" + str(int(round(weatherCur['WSD'])))    # 風

            '''
            if (val <= 4): weather_str += " 미약"
            elif (val <= 9): weather_str += " 약강"
            elif (val <= 14): weather_str += " 강"
            else : weather_str += " 강강"
            '''
        slen = draw.textsize(unicode(weather_str), font=font_gulim12)    # 하늘 상태
        if (slen[0] > 92):
            draw.text((0, 15), unicode(weather_str), font=font_gulim11, fill=255)    # 하늘 상태
        else:
            draw.text((0, 15), unicode(weather_str), font=font_gulim12, fill=255)    # 하늘 상태
    except:
        pass

#----------------------------------------------------------------------

NtpStat = None

def is_ntp_work():
    global NtpStat

    try:
        mesg = subprocess.check_output('ntpq -p', shell=True).splitlines()
        for i in range(len(mesg)):
            if ((mesg[i][0]) == '*'):
                NtpStat = True
                return
    except: pass
    NtpStat = False

#----------------------------------------------------------------------

week_str = ["月", "火", "水", "木", "金", "土", "日"]

def clock_common_disp():
    global NtpStat

    # 현재 시간
    localtime = time.localtime(time.time())
    month = localtime.tm_mon
    day = localtime.tm_mday
    hour = localtime.tm_hour
    minute = localtime.tm_min
    sec = localtime.tm_sec

    hour %= 24
    if (hour > 12): hour -= 12
    elif (hour == 0): hour = 12

    if (hour > 9): hx = 0
    else: hx = 7

    # 월 일 요일
    week = localtime.tm_wday % 7
    mesg = str('%2d' % month) + '월 ' + str('%2d' % day) + '일'
    draw.text((0, 32), unicode(mesg), font=font_gulim14, fill=255)
    draw.text((71, 32), unicode(week_str[week]), font=font_gulim16, fill=255)

    # 시 분 초 요일 표시
    time_hm = str('%2d' % hour) + ' : ' + str('%02d' % minute)
    time_s = str('%02d' % localtime.tm_sec)
    if (NtpStat == None or (NtpStat == False and (localtime.tm_sec % 10) == 0) or \
        (NtpStat and localtime.tm_sec == 0)): is_ntp_work()
    if (not NtpStat):
       time_s += '.'
    draw.text((hx, 48), time_hm, font=font_minecraftia14, fill=255)
    draw.text((61, 51), time_s, font=font_minecraftia12, fill=255)

#----------------------------------------------------------------------

#
# 시간 날씨 표시
#
def clock_disp():
    global NtpStat

    #ad = 4
    #localtime = time.localtime(time.time() + ad * (60 * 60 * 24))
    localtime = time.localtime(time.time())

    year = localtime.tm_year
    month = localtime.tm_mon
    day = localtime.tm_mday
    hour = localtime.tm_hour
    minute = localtime.tm_min
    sec = localtime.tm_sec

    now = datetime.datetime(year, month, day, hour, minute)

    # 요일 및 년 월 일
    week = localtime.tm_wday % 7
    time_ymd = str(year) + ' ' + str('%2d' % month) + ' '  + str('%2d' % day)

    # 이번주가 이번달의 몇번째 주일까?
    firstday = now.replace(day=1)
    firstday_week = firstday.weekday() % 7
    mw = int(ceil((day + firstday_week)/7.0))
    if (firstday_week > week): wmw = mw - 1
    else: wmw = mw

    # 그달의 첫주가 3일 이하면 그 다음주가 첫주가 된다고 함.
    # 좀 이상하지만 이것이 표준이라고 함
    # 그래서 첫주가 3일 이하면 0으로 표시됨.
    if (firstday_week > 3): # days of first week are less then 4
        mw -= 1
     
        ''' 
        # 그달의 첫주가 3일 이하면 그 전달의 마지막주를 표시한다.
        if (mw < 1):
            pm_lastday = now + datetime.timedelta(days=-day)
            firstday = pm_lastday.replace(day=1)
            firstday_week = firstday.weekday() % 7
            mw = int(ceil((pm_lastday.day + firstday_week)/7.0))
            if (firstday_week > 3): mw -= 1
        ''' 

    time_wmw = str(wmw)
    time_yw = str(mw) + '#' + str(now.isocalendar()[1])

    # 이번주 일요일이 2번째 또는 4번째 ?
    if (week < 6): add_days = 6 - week
    else: add_days = 0
    next_sunday = now + datetime.timedelta(days=add_days)
    firstday = next_sunday.replace(day=1)
    firstday_week = firstday.weekday() % 7
    smw = int(ceil((next_sunday.day + firstday_week)/7.0))

    if (hour >= 12):
        if (hour > 12):
            hour -= 12
        ampm = "pm"#'㏘'
    else:
        if (hour == 0): hour = 12
        ampm = "am"#'㏂'

    if(hour > 9): hx = 0
    else: hx = 10

    # 시 분 초 요일
    time_hm = str('%2d' % hour) + ' : ' + str('%02d' % minute)
    time_s = str('%02d' % localtime.tm_sec)
    if (NtpStat == None or (NtpStat == False and (localtime.tm_sec % 10) == 0) or \
        (NtpStat and localtime.tm_sec == 0)): is_ntp_work()
    if (not NtpStat):
       time_s += '.'
    time_w = week_str[week]

    # 년 월 일 주/년
    draw.text((0, 29), time_ymd, font=font_gulim16, fill=255)
    slen = draw.textsize(time_yw, font=font_gulim14)
    draw.text((128 - slen[0], 14), time_yw, font=font_gulim14, fill=255)

    # 이번주 일요일이 2번째 또는 4번째
    if (smw == 2) or (smw == 4):
        cir_num  = ['', '①', '②', '③', '④', '⑤']
        draw.text((110, 29), unicode(cir_num[wmw]), font=font_gulim16, fill=255)
    else: draw.text((114, 29), time_wmw, font=font_gulim14, fill=255)

    # 현재 시분초 요일 AM/PM
    draw.text((hx, 42), time_hm, font=font_minecraftia20, fill=255)
    draw.text((84, 50), time_s, font=font_minecraftia12, fill=255)
    draw.text((109, 44), unicode(time_w), font=font_gulim20, fill=255)
    draw.text((76, 39), unicode(ampm), font=font_gulim11, fill=255)

    # 날씨정보 요청 및 표시
    getWeatherCur(now)
    getWeatherFore(now)
    weather_disp(now)

    disp.image(image)
    disp.display()

#---------------------------------------------------------------
#
# 네트웍 상태 표시
#

init_net_mesg = "init network"

def network_disp():
    global init_net_mesg
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    mesg = subprocess.check_output('hostname', shell=True).splitlines()[0]
    draw.text((0, 0), unicode(mesg), font=font_gulim16, fill=255)

    mesg = subprocess.check_output('hostname -I', shell=True).splitlines()[0]
    mesg = mesg.split(' ')
    mlen = len(mesg)
    if (mlen > 0) and (mesg[0] != ''):
        draw.text((0, 24), mesg[0], font=font_gulim16, fill=255)
        if (mlen > 1):
            draw.text((0, 48), mesg[1], font=font_gulim16, fill=255)
        init_net_mesg = "init network"
    else:
        draw.text((0, 32), init_net_mesg, font=font_gulim16, fill=255)
        init_net_mesg += '.'

    disp.image(image)
    disp.display()
    return mesg

#---------------------------------------------------------------

t_tbl = [-14, -12, -10, -8, -6, -4, -2, 0, 14, 12, 10, 8, 6, 4, 2]
r_tbl = [0, 1, 2, 3, 4, 5, 6, 7, 14, 13, 12, 11, 10, 9, 8]
tda7439_info = {}

#---------------------------------------------------------------

def get_tda7439_gain():
    try:
        return tda7439_info['gain']
    except:
        return 0

#---------------------------------------------------------------

def get_tda7439():
    try:
        with open(tda7439_info_file, 'r') as fd:
            info = fd.read().splitlines()
        tda7439_info['power'] = int(info[0])
        tda7439_info['mute'] = int(info[1])
        tda7439_info['sel'] = 4 - int(info[3])
        tda7439_info['gain'] = int(info[4]) * 2
        tda7439_info['base'] = t_tbl[int(info[6])]
        tda7439_info['mid'] = t_tbl[int(info[7])]
        tda7439_info['treble'] = t_tbl[int(info[8])]
    except:
        pass

#---------------------------------------------------------------

def tda7439_disp():
    try:
        if (tda7439_info['power'] == 0): 
            draw.text((0, 0), unicode("TDA7439 꺼짐"), font=font_gulim14, fill=255)
        else:
            if ('gain' in tda7439_info.keys()): gain = str(tda7439_info['gain']) + " ㏈"
            else: gain = ""
            if ('base' in tda7439_info.keys()): base = str(tda7439_info['base']) + " ㏈"
            else: base = ""
            if ('mid' in tda7439_info.keys()): mid_range = str(tda7439_info['mid']) + " ㏈"
            else: mid_range = ""
            if ('treble' in tda7439_info.keys()): treble = str(tda7439_info['treble']) + " ㏈"
            else: treble = ""
    
            draw.text((0, 0), "Input gain: ", font=font_gulim14, fill=255)
            draw.text((0, 16), "Base gain: ", font=font_gulim14, fill=255)
            draw.text((0, 32), "Mid-Range: ", font=font_gulim14, fill=255)
            draw.text((0, 48), "Treble gain:", font=font_gulim14, fill=255)
            slen = draw.textsize(unicode(gain), font=font_gulim14)
            draw.text((128-slen[0], 0), unicode(gain), font=font_gulim14, fill=255)
            slen = draw.textsize(unicode(base), font=font_gulim14)
            draw.text((128-slen[0], 16), unicode(base), font=font_gulim14, fill=255)
            slen = draw.textsize(unicode(mid_range), font=font_gulim14)
            draw.text((128-slen[0], 32), unicode(mid_range), font=font_gulim14, fill=255)
            slen = draw.textsize(unicode(treble), font=font_gulim14)
            draw.text((128-slen[0], 48), unicode(treble), font=font_gulim14, fill=255)
    except:
        draw.text((0, 0), unicode("TDA7439 정보 없음"), font=font_gulim14, fill=255)

    disp.image(image)
    disp.display()

#---------------------------------------------------------------

prev_vol = None

def volume_disp(vol):
    global prev_vol

    if (('mute' in tda7439_info.keys() and tda7439_info['mute'] == 1)) or \
       ((vol != None) and (vol < 0)):
        disp_str = "Mute"
    else:
        if (vol == None): # 볼륨 정보가 없음을 의미함
            vol = prev_vol
        if (vol == None): # 여전히 볼륨 정보가 없음
            disp_str = "V ≡"
        else:
            gain = get_tda7439_gain()
            vol += gain
            if ('power' in tda7439_info.keys() and tda7439_info['power'] == 0): 
                if (gain > 0): disp_str = "∧:" + str(vol)
                else: disp_str = "∧ " + str(vol)
            else:
                if (gain > 0): disp_str = "V:" + str(vol)
                else: disp_str = "V " + str(vol)

    if (vol > 99):
        slen = draw.textsize(unicode(disp_str), font=font_gulim13)
        draw.text((128-slen[0], 52), unicode(disp_str), font=font_gulim13, fill=255)
    else:
        slen = draw.textsize(unicode(disp_str), font=font_gulim14)
        draw.text((128-slen[0], 51), unicode(disp_str), font=font_gulim14, fill=255)

    prev_vol = vol

#---------------------------------------------------------------

seq = 0
radio_station = ""
radio_station_num = -1
total_radio_station_num = -1

def inet_radio_disp():
    global radio_station, total_radio_station_num, radio_station_num
    global seq
    
    # Inet Radio Heart beat
    try:
        subprocess.check_output('ps -e | grep mplayer', shell=True) #.splitlines()[0]
        seq = (seq + 1) % 2
        draw.text((0, 0), unicode(music_note[seq]), font=font_gulim14, fill=255)
    except: pass

    # Inet Radio Title
    if (radio_station != ""):
        mesg = radio_station
    else:
        try:
            command = "egrep -aoi 'title[ .]*:.*$' " + inet_radio_mesg_file
            try: mesg = subprocess.check_output(command, shell=True).splitlines()
            except: mesg = ""
            if (mesg == ""): 
                command = "egrep -aoi 'name[ .]*:.*$' " + inet_radio_mesg_file
                mesg = subprocess.check_output(command, shell=True).splitlines()
            mesg = mesg[len(mesg)-1].split(':',1)[1].strip()
        except:
            mesg = "Radio " + str(radio_station_num+1)
    draw.text((18, 0), my_unicode(mesg), font=font_gulim14, fill=255)


    # 현재 번호 / 전체 station 수
    mesg = str(radio_station_num+1) + '/' + str(total_radio_station_num)
    if (radio_station_num+1 > 9): font = font_gulim13
    else: font = font_gulim14
    slen = draw.textsize(mesg, font=font)
    draw.text((128-slen[0], 32), mesg, font=font, fill=255)

    # 볼륨 정보
    try:
        #vol_str = subprocess.check_output("amixer get Digital | egrep -o '[0-9]+%' | awk -F % '{print $1}'", shell=True).splitlines()[0]
        vol_str = subprocess.check_output("mpc volume | egrep -o '[0-9]+%' | awk -F % '{print $1}'", shell=True).splitlines()[0]
        vol = int(vol_str)
    except:
        vol = None

    # Stream 정보
    try:
        # kbit
        command = "egrep -ao '[0-9.]* kbit' " + inet_radio_mesg_file
        mesg = subprocess.check_output(command, shell=True).splitlines()
        mesg = mesg[len(mesg)-1].split(' ',1)[0]
        if (mesg.split('.')[1] == '0'): stream_mesg1 = mesg.split('.')[0]
        else: stream_mesg1 = mesg
        stream_mesg1 += " kbps"
    except:
        stream_mesg1 = ""

    try:
        # 샘플링 주파수 Hz
        command = "egrep -ao '[0-9]* Hz' " + inet_radio_mesg_file
        mesg = subprocess.check_output(command, shell=True).splitlines()
        mesg = mesg[len(mesg)-1].split(' ',1)[0]
        q, r = divmod(int(mesg), 1000)
        if (r == 0): mesg = str(q) + " ㎑"
        else: mesg = str(float(mesg) / 1000) + " ㎑"
        stream_mesg2 = mesg
    except:
        stream_mesg2 = ""

    try:
        # 채널수 
        command = "egrep -ao '[0-9]* ch' " + inet_radio_mesg_file
        mesg = subprocess.check_output(command, shell=True).splitlines()
        mesg = mesg[len(mesg)-1]
        if (mesg == '1 ch'): stream_mesg3 = "Mono" # ⒨
        elif (mesg == '2 ch'): stream_mesg3 = "Stereo" # ⒮
        else: stream_mesg3 = mesg
    except:
        stream_mesg3 = ""

    stream_mesg = stream_mesg1 + "  " + stream_mesg2 + "  " + stream_mesg3
    slen =  draw.textsize(unicode(stream_mesg), font=font_gulim12)
    if (slen[0] > 133): # 1 pexel is margin
        stream_mesg = stream_mesg1 + " " + stream_mesg2 + " " + stream_mesg3
    elif (slen[0] > 129): # 1 pexel is margin
        stream_mesg = stream_mesg1 + " " + stream_mesg2 + "  " + stream_mesg3

    draw.text((0, 16), unicode(stream_mesg), font=font_gulim12, fill=255)

    # 볼륨 표시
    volume_disp(vol)

    # 시간 표시
    clock_common_disp()

    disp.image(image)
    disp.display()

#---------------------------------------------------------------

def usb_disp():
    draw.text((0, 0), unicode("Aux 입력"), font=font_gulim14, fill=255)

    # 볼륨 정보
    #vol_str = subprocess.check_output("amixer get Digital | egrep -o '[0-9]+%' | awk -F % '{print $1}'", shell=True).splitlines()[0]
    vol_str = subprocess.check_output("mpc volume | egrep -o '[0-9]+%' | awk -F % '{print $1}'", shell=True).splitlines()[0]
    vol = int(vol_str)

    # 볼륨 표시
    volume_disp(vol)

    # 시간 표시
    clock_common_disp()

    disp.image(image)
    disp.display()

#---------------------------------------------------------------

px1 = px2 = px3 = 0
wpx1 = wpx2 = wpx3 = 0 
prev_album = prev_title = prev_artist = ""
music_note = ['♬', '♪']
music_note_pos = 0
prev_sec = 0
#
# MPD 상태 표시
#
def mpd_disp():
    global px1, px2, px3
    global wpx1, wpx2, wpx3
    global prev_album, prev_title, prev_artist
    global music_note_pos, prev_sec

    mode = status['mode']
    album = status['album']
    title = status['title']
    artist = status['artist']
    state = status['state']
    eltime = status['eltime']
    play_time = status['play_time']
    random = status['random']
    vol = status['volume']

    if ((state != 'airplay') and eltime == 0) or (not (mode & 0x01) and \
        album != prev_album) or (title != prev_title) or (artist != prev_artist):
        px1 = wpx1 = px2 = wpx2 = px3 = wpx3 = 0

    prev_album = album
    prev_title = title
    prev_artist = artist

    # title
    slen = draw.textsize(my_unicode(title, errors='ignore'), font=font_gulim14)
    if (slen[0] > width): 
        title += "…     " + title
        if (px1 <= -(slen[0] + 39)): px1 = wpx1 = 0
        hscroll1 = True
    else: 
        px1 = (width - slen[0]) / 2
        hscroll1 = False
    draw.text((px1, 0), my_unicode(title, errors='ignore'), font=font_gulim14, fill=255)

    # artist
    slen = draw.textsize(my_unicode(artist, errors='ignore'), font=font_gulim14)
    if (slen[0] > width): 
        artist += "…     " + artist
        if (px2 <= -(slen[0] + 39)): px2 = wpx2 = 0
        hscroll2 = True
    else: 
        px2 = (width - slen[0]) / 2
        hscroll2 = False
    draw.text((px2, 15), my_unicode(artist, errors='ignore'), font=font_gulim14, fill=255)
    
    # album
    if (mode & 0x01): # radio stream의 경우 kbps, khz 정보 표시
        hscroll3 = False
        # VBS의 경우 bps 정보의 자릿수가 변경됨에 따른 디스플레이 흔들림 방지를 위해...
        mesg = album.split('kbps') # mesg[0]:kbps, mesg[1]:khz bits ch
        if (len(mesg) > 1 and int(mesg[0]) >= 500 and len(mesg[0]) < 6):
            if (len(mesg[0]) <= 4):
                draw.text((6, 34), my_unicode(mesg[0], errors='ignore'), font=font_gulim12, fill=255)
            else:
                draw.text((0, 34), my_unicode(mesg[0], errors='ignore'), font=font_gulim12, fill=255)
            mesg[1] = "kbps" + mesg[1]
            draw.text((28, 34), my_unicode(mesg[1], errors='ignore'), font=font_gulim12, fill=255)
        else:
            draw.text((0, 34), my_unicode(album, errors='ignore'), font=font_gulim12, fill=255)
    else:
        slen = draw.textsize(my_unicode(album, errors='ignore'), font=font_gulim14)
        if (slen[0] > width): 
            album += "…     " + album
            if (px3 <= -(slen[0] + 39)): px3 = wpx3 = 0
            hscroll3 = True
        else: 
            px3 = (width - slen[0]) / 2
            hscroll3 = False
        draw.text((px3, 32), my_unicode(album, errors='ignore'), font=font_gulim14, fill=255)

    # 볼륨
    volume_disp(vol)

    # Heart beat
    if (state != 'stop'):
        sec = time.localtime(time.time()).tm_sec
        if (sec != prev_sec):
            prev_sec = sec
            music_note_pos = (music_note_pos + 1) % 2
        draw.text((0, 52), unicode(music_note[music_note_pos]), font=font_gulim12, fill=255)
        #if ((seq % 12) < 6):  
        #    draw.text((0, 50), unicode("♬"), font=font_gulim12, fill=255)
        #else:
        #    draw.text((0, 52), unicode("♪"), font=font_gulim12, fill=255) # ♫

    # 경과시간
    if (state == 'stop'): mesg = "STOP"
    elif (state == 'airplay'): mesg = "AIRPLAY"
    else:
        h = eltime // 3600
        eltime %= 3600
        m = eltime // 60
        s = eltime % 60
        if (h > 0): mesg = "%d:%02d:%02d" % (h, m, s)
        else: mesg = "%02d:%02d" % (m, s)
    if (mode & 0x02):
        mesg += " dlna"
    else :
        mesg += "  "
        if (status['random'] == '1'): mesg += "R"
        if (status['repeat'] == '1'): mesg += "P"
    slen = draw.textsize(mesg, font=font_gulim14)
    if (slen[0] > 75):
        draw.text((16, 52), mesg, font=font_gulim13, fill=255)
    else:
        draw.text((16, 51), mesg, font=font_gulim14, fill=255)

    # Line for 경과시간
    if (play_time[1] > 0):
        px = play_time[0] * width / play_time[1]
        draw.line(((0, 50),(px,50)), fill=255)
        draw.rectangle((px-1, 49, px+1, 51), outline=1, fill=255)

    disp.image(image)
    disp.display()

    if ((wpx1 == 0) and (wpx2 == 0) and (wpx3 == 0)) or (state != 'play'):
        #seq += 3
        sleep(0.4)
    else:
        #seq += 1
        sleep(0.04)

    if (state == 'play') or (state == 'airplay'):
        if (hscroll1):
            wpx1 += 1
            if (wpx1 > 20): px1 = px1 - 3
        if (hscroll2):
            wpx2 += 1
            if (wpx2 > 20): px2 = px2 - 3
        if (hscroll3):
            wpx3 += 1
            if (wpx3 > 20): px3 = px3 - 3

#=====================================================================

clock_sleep_time = 0.85
#import timeit
def main():
    global disp, image, draw
    global width, height
    global status
    global disp_mode
    global my_network
    global showStreamInfo

    get_disp_mode()
    get_tda7439()
    signal.signal(signal.SIGUSR1, sig_handler)

    # 128x64 display with hardware I2C:
    disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

    # Initialize library.
    disp.begin()

    # Clear display.
    disp.clear()
    disp.display()

    # Create blank image for drawing.
    # Make sur<e to create image with mode '1' for 1-bit color.
    width = disp.width
    height = disp.height
    image = Image.new('1', (width, height))

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    poller = MPDPoller()
    if (poller.connect() != 0):
        while True:
            mesg = network_disp()
            if (len(mesg) > 0) and (mesg[0] != ''): 
                sleep(1)
                poller.connect()
                break
            sleep(0.9)

    if (len(sys.argv) > 1): 
        disp_mode = sys.argv[1] 

    # DLNA stream을 radio stream과 구분하기 위해 network 주소를 알 필요가 있음
    my_network = "http://192.168"
    mesg = subprocess.check_output('hostname -I', shell=True).splitlines()[0]
    mesg = mesg.split(' ')
    mlen = len(mesg)
    if (mlen > 0) and (mesg[0] != ''):
        my_network = "http://" + mesg[0].rsplit('.', 2)[0]

    while True:
        draw.rectangle((0,0,width,height), outline=0, fill=0)

        # 네트워크 상태 디스플레이
        if (disp_mode == 'network'):
            mesg = network_disp()
            sleep(0.9)
            continue

        elif (disp_mode == 'clock'):
#            st = timeit.default_timer()
            clock_disp()
#            et = timeit.default_timer()
#            print(et-st)
            sleep(clock_sleep_time)
            continue

        elif (disp_mode == 'tda7439'):
            tda7439_disp()
            sleep(0.9)
            continue

        elif (disp_mode == 'inet_radio'):
            if (len(sys.argv) > 2): station = sys.argv[2]
            else: station=''
            inet_radio_disp()
            sleep(0.9)
            continue

        elif (disp_mode == 'usb'):
            usb_disp()
            sleep(0.9)
            continue

        # auto 모드는 처음 부팅하고 나서 다른 모드로 전환하기 전까지 임시로 사용.
        if (disp_mode == 'auto'):
            try:
                subprocess.check_output('ps -e | grep mplayer', shell=True) #.splitlines()[0]
                inet_radio_disp()
                sleep(0.9)
                continue
            except: pass

            status = poller.poll()
            if status is None or status['state'] == 'stop':
                clock_disp()
                sleep(clock_sleep_time)
                continue
            mpd_disp()
            continue

        # else mpd 모드
        # MPD stream 정보 표시 여부
        if (disp_mode == 'info'):
            showStreamInfo = True
        else:
            showStreamInfo = False

        status = poller.poll()
        if status is None:
            clock_disp()
            sleep(clock_sleep_time)
            continue

        mpd_disp()


if __name__ == "__main__":
    try:
        main()

    # Catch fatal poller errors
    except PollerError as e:
        pass
        #sys.stderr.write("Fatal poller error: %s" % e)
        #sys.exit(1)

    '''
    # Catch all other non-exit errors
    except Exception as e:
        pass
        #sys.stderr.write("Unexpected exception: %s" % e)
        #disp.clear()
        #disp.display()
        #sys.exit(1)

    # Catch the remaining exit errors
    except:
        pass
        #disp.clear()
        #disp.display()
        #sys.exit(0)
    '''
