# main.py
# Non-blocking 1000 ms tick using uasyncio.
# - Connects Wi-Fi
# - Syncs RTC from NTP (UTC)
# - Connects MQTT and subscribes
# - Publishes state every second without blocking
# - Services MQTT in background and keeps connection alive

import machine
import time
from time import gmtime
from machine import Pin
import network
import select, struct
from mqtt import MQTTClient
import ujson as json

try:
    import usocket as socket
except:
    import socket

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio  # if running on CPython for testing only

# ---------- Config ----------
DEBUGGING = True
LED_PIN = 15
STRING_LED_PIN = 5
SLEEP_LED_MS = 50  # brief indicator blinks

from config import *

ntp_host = config["time_server"]

mqtt_host = config["mqtt_host"]
mqtt_clientid = config["mqtt_clientid"]  # e.g. "letterbox1"
mqtt_username = config["mqtt_username"] or None
mqtt_password = config["mqtt_password"] or None
KEEPALIVE_S = 60

TOPIC_SET = (mqtt_clientid + "/set").encode()
TOPIC_STATE = (mqtt_clientid + "/state").encode()

# ---------- Globals ----------
NTP_DELTA = 3155673600 if gmtime(0)[0] == 2000 else 2208988800
rtc = machine.RTC()
wlan = network.WLAN(network.STA_IF)
led = Pin(LED_PIN, Pin.OUT)
led_string = Pin(STRING_LED_PIN, Pin.OUT)

state = {"enabled": False, "on": False, "date_time": rtc.datetime()}


def dprint(*a):
    if DEBUGGING:
        print(*a)


def now_ms():
    return time.ticks_ms()


def ms_since(t0):
    return time.ticks_diff(time.ticks_ms(), t0)


# ---------- Utilities ----------
async def blink(n=1, t_ms=SLEEP_LED_MS):
    for _ in range(n):
        led.value(1)
        await asyncio.sleep_ms(t_ms)
        led.value(0)
        await asyncio.sleep_ms(t_ms)


def ts_time_utc() -> int:
    """Return current UTC epoch seconds from NTP or 0 on failure."""
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
        if poller.poll(1000):  # 1s timeout
            msg = s.recv(48)
            val = struct.unpack("!I", msg[40:44])[0]
            return max(val - NTP_DELTA, 0)
    except OSError:
        pass
    finally:
        s.close()
    return 0


def set_rtc_from_ntp():
    """Set RTC to UTC. Weekday is dt[6]. Subseconds=0."""
    t = ts_time_utc()
    if not t:
        return False
    dt = gmtime(t)  # (Y,M,D,h,m,s,wday,yday)
    rtc.datetime((dt[0], dt[1], dt[2], dt[6], dt[3], dt[4], dt[5], 0))
    return True


def mqtt_publish(client, topic, data):
    # JSON -> bytes
    payload = json.dumps(data).encode()
    client.publish(topic, payload)


def mqtt_make_on_msg(client):
    def mqtt_on_msg(topic, msg):
        dprint("MQTT:", topic, msg)
        try:
            data = json.loads(msg.decode())
        except Exception as e:
            dprint("JSON parse error:", e)
            return

        if "enabled" in data:
            state["enabled"] = bool(data["enabled"])
        if "on" in data:
            state["on"] = bool(data["on"])

        led.value(1 if state["enabled"] else 0)
        led_string.value(1 if state["on"] else 0)
        mqtt_publish(client, TOPIC_STATE, state)  # uses captured client

    return mqtt_on_msg


# ---------- Wi-Fi ----------
async def wifi_connect():
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(config["wlan_ssid"], config["wlan_pwd"])
        # Wait up to 15s without blocking loop
        for _ in range(150):
            if wlan.isconnected():
                break
            await asyncio.sleep_ms(100)
    if not wlan.isconnected():
        return False
    dprint("Wi-Fi:", wlan.ifconfig())
    return True


# Periodic Wi-Fi guard. Resets on disconnect.
async def wifi_guard():
    while True:
        if not wlan.isconnected():
            dprint("Wi-Fi lost. Resetting.")
            machine.reset()
        await asyncio.sleep_ms(1000)


# ---------- MQTT ----------
def mqtt_connect():
    c = MQTTClient(
        client_id=mqtt_clientid,
        server=mqtt_host,
        user=mqtt_username,
        password=mqtt_password,
        keepalive=KEEPALIVE_S,
    )
    c.set_callback(mqtt_make_on_msg(c))
    c.connect()
    c.subscribe(TOPIC_SET, qos=0)
    return c


async def mqtt_service(client):
    last_ping = now_ms()
    while True:
        try:
            client.check_msg()
        except OSError:
            machine.reset()

        if ms_since(last_ping) > (KEEPALIVE_S * 800):  # ~0.8*keepalive
            try:
                client.ping()
            except OSError:
                machine.reset()
            last_ping = now_ms()

        await asyncio.sleep_ms(20)


# ---------- 1 Hz Tick ----------
async def tick_1hz(client):
    period = 10000  # ms
    while True:
        t0 = now_ms()

        state["date_time"] = rtc.datetime()
        try:
            mqtt_publish(client, TOPIC_STATE, state)
        except OSError:
            machine.reset()

        # sleep the remainder of the 1000 ms slot
        rem = period - ms_since(t0)
        if rem < 0:
            rem = 0
        await asyncio.sleep_ms(rem)


# ---------- Main ----------
async def main():
    await blink(2, 100)

    if not await wifi_connect():
        # slow blink → no Wi-Fi, then reset
        await blink(10, 250)
        machine.reset()

    if set_rtc_from_ntp():
        await blink(3, 150)  # RTC set indicator
    else:
        dprint("NTP failed; keeping previous RTC")

    try:
        mqtt_client = mqtt_connect()
    except OSError:
        dprint("MQTT connect failed. Resetting.")
        machine.reset()

    await blink(3, 300)  # MQTT connected indicator

    # Publish initial state
    try:
        mqtt_publish(mqtt_client, TOPIC_STATE, state)
    except OSError:
        machine.reset()

    # Launch tasks
    asyncio.create_task(wifi_guard())
    asyncio.create_task(mqtt_service(mqtt_client))
    await tick_1hz(mqtt_client)  # never returns


# Run
try:
    asyncio.run(main())
finally:
    try:
        asyncio.new_event_loop()
    except:
        pass
