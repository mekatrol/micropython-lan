import network
from machine import Pin
from time import sleep
from config import *

# The NTP host can be configured at runtime by doing: ntptime.host = 'myhost.org'
ntp_host = config["time_server"]

# WLAN connected status flag
is_wlan_connected = False
wlan_ip = "not set"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

led = Pin(15, Pin.OUT)


def wlan_connect(ssid, pwd):
    global wlan
    wlan.disconnect()
    sleep(1)
    wlan.connect(ssid, pwd)

    # Wait for connect or fail
    wait = 30
    while wait > 0:
        print("Trying to connect to WLAN...")
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


# Connect to WLAN
print("Connecting to WLAN")
wlan_init()

print(f"IP: {wlan_ip}")

while True:
    for _ in range(10):
        led.value(1)
        sleep(0.5)
        led.value(0)
        sleep(0.5)
