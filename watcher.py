"""Watch Dog."""
from machine import WDT

__wdt = None
__enabled = True


def wdt():
    """Obtain watchdog."""
    global __wdt
    if not __wdt:
        __wdt = WDT(timeout=15000)
    return __wdt


def feed():
    """Feed the watchdog."""
    global __enabled
    if __enabled:
        wdt().feed()


def disable():
    """Disable watchdog."""
    global __enabled
    __enabled = False
