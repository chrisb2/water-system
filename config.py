"""Configuration property values."""
from machine import Pin
import urtc

# NZDT, 13 hours ahead
HOURS_DIFF_FROM_GMT = 13

# Voltage ratio between voltage after division by resistor network and
# battery voltage (determine with multimeter)
RESISTOR_RATIO = 3.97

# System wakeup time Properties
# 5AM GMT
RTC_ALARM = urtc.datetime_tuple(None, None, None, None, 5, 0, None, None)
# Every hour
# RTC_ALARM = urtc.datetime_tuple(None, None, None, None, None, 0, None, None)
# Time to sleep between attempts to connect to WiFi
SLEEP_ONE_MINUTE = \
    urtc.datetime_tuple(None, None, None, None, None, None, 0, None)

SCL_PIN = Pin(7)
SDA_PIN = Pin(6)
WAKEUP_PIN = Pin(4, Pin.IN, Pin.PULL_UP)
WATER_ON_PIN = Pin(3, Pin.OUT, Pin.PULL_DOWN, value=0)
WATER_OFF_PIN = Pin(2, Pin.OUT, Pin.PULL_DOWN, value=0)
NO_SLEEP_PIN = Pin(21, Pin.IN, Pin.PULL_DOWN, value=0)
BATTERY_PIN = Pin(5)  # ADC

# Number of ADC reads to take average of
ADC_READS = 100

# WiFi retry - time system will sleep for if WiFi connect fails
WIFI_RETRY_MINS = 5
