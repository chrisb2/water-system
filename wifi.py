"""WiFi configuration."""
import network
from utime import ticks_ms, ticks_diff, sleep
import secrets

WIFI_DELAY = 5


def connect():
    """Connect to WiFi."""
    start = ticks_ms()

    print('Connecting to network...')

    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect(secrets.WIFI_SSID, secrets.WIFI_PASSPHRASE)

    secs = WIFI_DELAY
    while secs >= 0 and not sta_if.isconnected():
        sleep(1)
        secs -= 1
    if sta_if.isconnected():
        print('Network, address: %s in %d ms' %
              (sta_if.ifconfig()[0], ticks_diff(ticks_ms(), start)))
