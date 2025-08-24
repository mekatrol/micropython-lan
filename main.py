import rp2
from machine import Pin
from time import sleep
import network
import socket
import struct
import select
import gc
from time import gmtime
from config import *
from http import WebApp, jsonify

# Make sure watchdog disabled as first priority
wdePin = Pin(14, Pin.OUT)
wdePin.high()

led = machine.Pin("LED", machine.Pin.OUT)

try:
    import usocket as socket
except:
    import socket

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

webapp = WebApp()

outputs = 0x00000000

gc.collect()

# The NTP host can be configured at runtime by doing: ntptime.host = 'myhost.org'
ntp_host = config["time_server"]

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

outputEnablePin = Pin(13, Pin.OUT, Pin.PULL_UP)
outputEnablePin.high()


# The data pin is the output (default low), clock is size set bit 0 (default high), latch is side set bit 1 (default low)
@rp2.asm_pio(out_init=rp2.PIO.OUT_LOW, sideset_init=(rp2.PIO.OUT_HIGH, rp2.PIO.OUT_LOW))
def pio_prog():
    wrap_target()
    pull(ifempty)
    label("bitloop")
    out(pins, 1)
    nop().side(0x00)[1]  # clear clock
    nop().side(0x01)[1]  # set clock clock
    jmp(not_osre, "bitloop")  # loop if 8 bits not shifted
    nop().side(0x03)[1]  # set latch
    nop().side(0x01)[1]  # clear latch
    wrap()


# Pin(10) is the data pin, Pin(11) is the clock pin and Pin(12) is the latch pin
sm0 = rp2.StateMachine(0, pio_prog, freq=2000, out_base=Pin(10), sideset_base=Pin(11))
sm0.active(1)

# 32 bits means can have up to 4 x 74HC595 chained
sm0.put(outputs)
outputEnablePin.low()


def get_output(name):
    global outputs

    value = 0
    if name == "op1":
        value = (outputs >> 0) & 1
    if name == "op2":
        value = (outputs >> 1) & 1
    if name == "op3":
        value = (outputs >> 2) & 1
    if name == "op4":
        value = (outputs >> 3) & 1
    if name == "op5":
        value = (outputs >> 4) & 1
    if name == "op6":
        value = (outputs >> 5) & 1
    if name == "op7":
        value = (outputs >> 6) & 1
    if name == "op8":
        value = (outputs >> 7) & 1
    if name == "op9":
        value = (outputs >> 8) & 1
    if name == "op10":
        value = (outputs >> 9) & 1
    if name == "op11":
        value = (outputs >> 10) & 1
    if name == "op12":
        value = (outputs >> 11) & 1
    if name == "op13":
        value = (outputs >> 12) & 1
    if name == "op14":
        value = (outputs >> 13) & 1
    if name == "op15":
        value = (outputs >> 14) & 1
    if name == "op16":
        value = (outputs >> 15) & 1
    else:
        op_resp = {}
        op_resp["error"] = f"Unknown output {name}"
        op_resp["value"] = value

    op_resp = {}
    op_resp["name"] = name
    op_resp["value"] = value

    return op_resp


def update_output(name, value):
    global outputs

    mask = 0
    shifted_value = 0

    if name == "op1":
        mask = 1
        shifted_value = value << 0
    if name == "op2":
        mask = 2
        shifted_value = value << 1
    if name == "op3":
        mask = 4
        shifted_value = value << 2
    if name == "op4":
        mask = 8
        shifted_value = value << 3
    if name == "op5":
        mask = 16
        shifted_value = value << 4
    if name == "op6":
        mask = 32
        shifted_value = value << 5
    if name == "op7":
        mask = 64
        shifted_value = value << 6
    if name == "op8":
        mask = 128
        shifted_value = value << 7
    if name == "op9":
        mask = 256
        shifted_value = value << 8
    if name == "op10":
        mask = 512
        shifted_value = value << 9
    if name == "op11":
        mask = 1024
        shifted_value = value << 10
    if name == "op12":
        mask = 2048
        shifted_value = value << 11
    if name == "op13":
        mask = 4096
        shifted_value = value << 12
    if name == "op14":
        mask = 8192
        shifted_value = value << 13
    if name == "op15":
        mask = 16384
        shifted_value = value << 14
    if name == "op16":
        mask = 32768
        shifted_value = value << 15
    else:
        op_resp = {}
        op_resp["error"] = f"Unknown output {name}"
        op_resp["value"] = value

    mask_inv = mask ^ 0xFFFFFFFF
    outputs = outputs & mask_inv
    outputs = outputs | (shifted_value & mask)
    op_resp = {}
    op_resp["name"] = name
    op_resp["value"] = value

    return op_resp


@webapp.route("/", method="GET")
def index(request, response):
    global outputs
    obj = {}
    obj["outputs"] = outputs
    gc.collect()
    yield from jsonify(response, obj)


@webapp.route("/outputs/1", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op1")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/2", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op2")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/3", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op3")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/4", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op4")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/5", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op5")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/6", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op6")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/7", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op7")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/8", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op8")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/9", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op9")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/10", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op10")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/11", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op11")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/12", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op12")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/13", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op13")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/14", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op14")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/15", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op15")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/16", method="GET")
def index(request, response):
    global outputs
    op_resp = get_output("op16")
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/1", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op1", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/2", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op2", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/3", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op3", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/4", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op4", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/5", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op5", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/6", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op6", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/7", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op7", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/8", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op8", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/9", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op9", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/10", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op10", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/11", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op11", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/12", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op12", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/13", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op13", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/14", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op14", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/15", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op15", value)
    gc.collect()
    yield from jsonify(response, op_resp)


@webapp.route("/outputs/16", method="POST")
def set_outputs(request, response):
    global outputs
    yield from request.read_json()
    value = request.json["value"]
    op_resp = update_output("op16", value)
    gc.collect()
    yield from jsonify(response, op_resp)


def wlan_connect(ssid, pwd):
    wlan.disconnect()
    wlan.connect(ssid, pwd)

    # Wait for connect or fail
    wait = 30
    while wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        wait -= 1
        sleep(1)


def wlan_connected():
    return wlan.status() == 3


def wlan_init():
    global is_wlan_connected
    global wlan_ip

    # Get preferred WAN SSID and password from config file
    wlan_ssid = config["wlan_ssid"]
    wlan_pwd = config["wlan_pwd"]

    # Connect to WLAN
    wlan_connect(wlan_ssid, wlan_pwd)

    # If WLAN did not connect then try fallback SSID and password
    if not wlan_connected():
        wlan_ssid = config["wlan_ssid_fallback"]
        wlan_pwd = config["wlan_pwd_fallback"]
        wlan_connect(wlan_ssid, wlan_pwd)

    # Handle connection error
    if not wlan_connected():
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
    rtc.datetime((dt[0], dt[1], dt[2], dt[7], dt[3], dt[4], dt[5], dt[6]))


async def update_outputs():
    while True:
        await asyncio.sleep(1)
        sm0.put(outputs)
        gc.collect()


print("Connecting to WLAN")
wlan_init()

if wlan_ip != "not set":
    led.on()

print(f"IP: {wlan_ip}")

print("Getting date/time")
refresh_date_time()
print(f"Date/time: {rtc.datetime()}")

# Loop forever
while True:
    # If WLAN is not connected then try and reconnect
    while not wlan_connected():
        # Sleep for two seconds
        sleep(2)

        # Initialise WLAN
        wlan_init()
        continue

    loop = asyncio.get_event_loop()
    loop.create_task(update_outputs())
    loop.create_task(asyncio.start_server(webapp.handle, "0.0.0.0", 80))
    gc.collect()
    loop.run_forever()
    sm0.put(outputs)
