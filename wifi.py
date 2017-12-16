"""WiFi configuration."""
import network
from utime import ticks_ms, ticks_diff
import secrets

WIFI_DELAY = 5
net_conf = ('192.168.1.25', '255.255.255.0', '192.168.1.1', '8.8.8.8')


def connect():
    """Connect to WiFi."""
    start = ticks_ms()

    print('Connecting to network...')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.ifconfig(net_conf)
    wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSPHRASE)

    if wlan.isconnected():
        print('Network to address %s in %dms' %
              (wlan.ifconfig()[0], ticks_diff(ticks_ms(), start)))
