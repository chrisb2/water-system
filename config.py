"""Configuration property values."""
import urtc
from machine import Pin

# Wunderground API properties
WUNDERGROUND_STATION = '/pws:ICANTERB161'
WUNDERGROUND_LOCATION = 'zmw:00000.7.93781'

# Resistor Divider properties (Ohms)
R1 = 10070000
R2 = 3329000
# External resister divider (ohms)
RESISTOR_RATIO = (R1 + R2) / R2

# ESP32 properties
# ADC reference voltage in millivolts (adjust for each ESP32)
ADC_REF = 1165

# System wakeup time Properties
# 5AM GMT
RTC_ALARM = urtc.datetime_tuple(None, None, None, None, 5, 0, None, None)
# Every hour
# RTC_ALARM = urtc.datetime_tuple(None, None, None, None, None, 0, None, None)
# Every minute
# RTC_ALARM = urtc.datetime_tuple(None, None, None, None, None, None, 0, None)

# Std Micropython
I2C_PERIPHERAL = -1

# Loboris MicroPython
# I2C_PERIPHERAL = 1

SCL_PIN = Pin(17)
SDA_PIN = Pin(5)
WAKEUP_PIN = Pin(4, Pin.IN, Pin.PULL_UP)
WATER_ON_PIN = Pin(33, Pin.OUT, Pin.PULL_DOWN, value=0)
WATER_OFF_PIN = Pin(32, Pin.OUT, Pin.PULL_DOWN, value=0)
NO_SLEEP_PIN = Pin(26, Pin.IN, Pin.PULL_DOWN, value=0)
BATTERY_PIN = Pin(34)  # ADC

# Number of ADC reads to take average of
ADC_READS = 100
