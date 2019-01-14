"""WiFi configuration."""
import network
from utime import ticks_ms, ticks_diff, sleep
import secrets
import clock
from retrier import retry
from file_logger import File

WIFI_DELAY = 10
CHECK_INTERVAL = 0.5


@retry(Exception, tries=5, delay=2, backoff=2.0, logger=File.logger())
def connect():
    """Connect to WiFi."""
    start = ticks_ms()

    sleep(CHECK_INTERVAL)
    File.logger().info('%s - Connecting to network...', clock.timestamp())

    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect(secrets.WIFI_SSID, secrets.WIFI_PASSPHRASE)

    secs = WIFI_DELAY
    while secs >= 0 and not sta_if.isconnected():
        File.logger().info('%s - Waiting...', clock.timestamp())
        sleep(CHECK_INTERVAL)
        secs -= CHECK_INTERVAL

    if sta_if.isconnected():
        File.logger().info('%s - Connected, address: %s in %d ms',
                           clock.timestamp(),
                           sta_if.ifconfig()[0], ticks_diff(ticks_ms(), start))
    else:
        sta_if.active(False)
        raise RuntimeError('%s - WiFi did not connect' % clock.timestamp())


def disconnect():
    """Disconnect from WiFi."""
    sta_if = network.WLAN(network.STA_IF)
    if sta_if.isconnected():
        sta_if.disconnect()

    secs = WIFI_DELAY
    while secs >= 0 and sta_if.isconnected():
        sleep(CHECK_INTERVAL)
        secs -= CHECK_INTERVAL

    sta_if.active(False)


def enable_ftp():
    """Enable FTP."""
    network.ftp.start()
    while network.ftp.status()[2] != 'Ready':
        sleep(0.2)
    print(network.ftp.status()[4])
