import machine
from machine import Pin
import network
import select
import struct
from time import sleep, gmtime
from umqtt.simple import MQTTClient
from config import *

try:
    import usocket as socket
except:
    import socket

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

DEBUGGING = True
LED_PIN = 15
SLEEP_MS = 10000  # 10 seconds

# The NTP host can be configured at runtime by doing: ntptime.host = 'myhost.org'
ntp_host = config["time_server"]

mqtt_host = config["mqtt_host"]
mqtt_clientid = config["mqtt_clientid"]
mqtt_username = config["mqtt_username"]
mqtt_password = config["mqtt_password"]

# (date(2000, 1, 1) - date(1900, 1, 1)).days * 24*60*60
# (date(1970, 1, 1) - date(1900, 1, 1)).days * 24*60*60
NTP_DELTA = 3155673600 if gmtime(0)[0] == 2000 else 2208988800

# Get real time clock
rtc = machine.RTC()

# WLAN connected status flag
is_wlan_connected = False
wlan_ip = "not set"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

led = Pin(15, Pin.OUT)

state = {"enabled": False, "on": False, "date_time": rtc.datetime()}


def DEBUG_PRINT(s):
    if not DEBUGGING:
        return

    print(s)


def wlan_connect(ssid, pwd):
    global wlan
    wlan.disconnect()
    sleep(1)
    wlan.connect(ssid, pwd)

    # Wait for connect or fail
    wait = 30
    while wait > 0:
        if wlan.isconnected():
            break
        wait -= 1
        sleep(1)


def wlan_init():
    global is_wlan_connected
    global wlan_ip
    global wlan

    # Get preferred WAN SSID and password from config file
    wlan_ssid = config["wlan_ssid"]
    wlan_pwd = config["wlan_pwd"]

    # Connect to WLAN
    wlan_connect(wlan_ssid, wlan_pwd)

    # Handle connection error
    if not wlan.isconnected():
        is_wlan_connected = False
    else:
        wlan_ip = wlan.ifconfig()[0]
        is_wlan_connected = True


def ts_time(hrs_offset=0):  # Local time offset in hrs relative to UTC
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    try:
        addr = socket.getaddrinfo(ntp_host, 123)[0][-1]
    except OSError:
        return 0
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    poller = select.poll()
    poller.register(s, select.POLLIN)
    try:
        s.sendto(NTP_QUERY, addr)
        if poller.poll(1000):  # time in milliseconds
            msg = s.recv(48)
            val = struct.unpack("!I", msg[40:44])[0]  # Can return 0
            return max(val - NTP_DELTA + hrs_offset * 3600, 0)
    except OSError:
        pass  # LAN error
    finally:
        s.close()
    return 0  # Timeout or LAN error occurred


def refresh_date_time():
    if not is_wlan_connected:
        return  # Can't refresh date / time if WLAN not connected

    # gmtime returns time.struct_time
    # 0 tm_year (for example, 1993)
    # 1 tm_mon  range [1, 12]
    # 2 tm_mday range [1, 31]
    # 3 tm_hour range [0, 23]
    # 4 tm_min  range [0, 59]
    # 5 tm_sec  range [0, 61]
    # 6 tm_wday range [0, 6], Monday is 0
    # 7 tm_yday range [1, 366]
    # 8 tm_isdst    0, 1 or -1

    dt = gmtime(ts_time(11))

    # rtc.datetime takes tuple (year, month, day, weekday, hours, minutes, seconds, subseconds)
    rtc.datetime((dt[0], dt[1], dt[2], dt[7], dt[3], dt[4], dt[5], 0))


def blink(n=2, t=0.2):
    for _ in range(n):
        led.value(1)
        sleep(t)
        led.value(0)
        sleep(t)


# Connect to WLAN
DEBUG_PRINT("Initialising WLAN...")
wlan_init()

if not wlan.isconnected():
    # 10 slow blinks to indicate WLAN not connected
    blink(n=10, t=0.5)

    # Reset device
    machine.reset()

# 5 quick blinks to indicate WIFI connected
blink(n=5, t=0.2)

DEBUG_PRINT("Initialising Date/Time...")
refresh_date_time()

# 3 slow blinks to indicate date/time set
blink(n=3, t=0.5)

# Create MQTT client
mqtt_client = MQTTClient(
    client_id=mqtt_clientid,
    server=mqtt_host,
    user=mqtt_username,
    password=mqtt_password,
)

mqtt_client.connect()

# 3 really slow blinks to indicate MQTT connected
blink(n=3, t=1)

# Publish letterbox connected state
mqtt_client.publish(f"{mqtt_clientid}/state", f"{state}")

sleep_time = 0.1
while True:
    # Only go into light sleep if not debugging
    if not DEBUGGING:
        machine.lightsleep(SLEEP_MS)
    else:
        sleep(SLEEP_MS / 1000)

    sleep_time = 0.5

    # Test if need to reconnect WLAN
    try:
        if wlan.isconnected():
            sleep_time = 0.1
        else:
            raise RuntimeError("Disconnected from WLAN")
    except:
        # If WLAN no longer connected so reset from begining
        machine.reset()

    # 3 flashes to indicate WLAN state when woke from light sleep
    blink(n=3, t=sleep_time)

    state["date_time"] = rtc.datetime()
    mqtt_client.publish(f"{mqtt_clientid}/state", f"{state}")
