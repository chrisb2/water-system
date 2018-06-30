"""Configuration property values."""
import urtc

# Wunderground API properties
WUNDERGROUND_STATION = '/pws:ICANTERB161'
WUNDERGROUND_LOCATION = 'zmw:00000.7.93781'

# Resistor Divider properties (Ohms)
R1 = 10070000
R2 = 3329000

# ESP32 properties
# ADC reference voltage in millivolts (adjust for each ESP32)
ADC_REF = 1165

# System wakeup time Properties
# 5AM GMT
# RTC_ALARM = urtc.datetime_tuple(None, None, None, None, 5, 0, None, None)
# Every hour
RTC_ALARM = urtc.datetime_tuple(None, None, None, None, None, 0, None, None)
# Every minute
# RTC_ALARM = urtc.datetime_tuple(None, None, None, None, None, None, 0, None)

# Std Micropython
I2C_PERIPHERAL = -1

# Loboris MicroPython
# I2C_PERIPHERAL = 1
