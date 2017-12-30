"""Monitor local rainfall and disable garden watering system if required."""
import urequests
from machine import Pin, ADC
import machine
import esp32
import utime
import urtc
import secrets

INTERRUPT_PIN = Pin(4, Pin.IN, Pin.PULL_UP)
SCL_PIN = Pin(17)
SDA_PIN = Pin(5)
WATER_ON_PIN = Pin(25, Pin.OUT, Pin.PULL_DOWN, value=0)
WATER_OFF_PIN = Pin(26, Pin.OUT, Pin.PULL_DOWN, value=0)
NO_SLEEP_PIN = Pin(27, Pin.IN, Pin.PULL_DOWN, value=0)
BATTERY_PIN = Pin(32)  # ADC

# External resister divider (ohms)
R1 = 330000
R2 = 100200
RESISTOR_RATIO = (R1 + R2) / R2

# ADC reference voltage in millivolts
ADC_REF = 1112
# Average value from 100 reads when analog pin is grounded
ADC_OFFSET = 0
# Number of ADC reads to take average of
ADC_READS = 100

_THINGSPEAK_URL = \
   'https://api.thingspeak.com/update?api_key={}&field1={}&field2={}&field3={}'
_WEATHER_URL = \
   'http://api.wunderground.com/api/{}/conditions/q{}.json'

# 5AM GMT
# RTC_ALARM = urtc.datetime_tuple(None, None, None, None, 5, 0, None, None)
RTC_ALARM = urtc.datetime_tuple(None, None, None, None, None, 0, None, None)


def run():
    """Main entry point to execute this program."""
    sleep_enabled = _sleep_enabled()

    battery_volts = _battery_voltage()
    try:
        rain_last_hour_mm, rain_today_mm = _read_from_wunderground()
        _send_to_thingspeak(rain_last_hour_mm, rain_today_mm, battery_volts)
    except Exception:
        # Catch exceptions so that device goes back to sleep if HTTP calls fail
        rain_last_hour_mm, rain_today_mm = (0, 0)

    if rain_today_mm > 3 or rain_last_hour_mm > 1:
        _system_off()
    else:
        _system_on()

    if sleep_enabled:
        _sleep_until(RTC_ALARM)


def datetime():
    """Get current date/time from RTC."""
    return _get_rtc().datetime()


def _sleep_until(alarm_time):
    _configure_pin_interrupt()
    _configure_rtc_alarm(alarm_time)
    print('Sleeping...')
    machine.deepsleep()


def _configure_pin_interrupt():
    esp32.wake_on_ext0(INTERRUPT_PIN, 0)


def _get_rtc():
    i2c = machine.I2C(-1, SCL_PIN, SDA_PIN)
    return urtc.DS3231(i2c)


def _configure_rtc_alarm(alarm_time):
    rtc = _get_rtc()

    rtc.alarm(0, alarm=1)  # Clear previous alarm state of RTC
    rtc.interrupt(alarm=1)  # Configure alarm on INT/SQW pin of RTC
    rtc.alarm_time(alarm_time, alarm=1)  # Configure alarm time of RTC


def _send_to_thingspeak(rain_last_hour_mm, rain_today_mm, battery_volts):
    url = _THINGSPEAK_URL.format(secrets.THINGSPEAK_API_KEY,
                                 rain_last_hour_mm, rain_today_mm,
                                 battery_volts)
    req = urequests.get(url)
    req.close()


def _read_from_wunderground():
    url = _WEATHER_URL.format(secrets.WUNDERGROUND_API_KEY,
                              secrets.WUNDERGROUND_STATION)
    req = urequests.get(url)
    observation = req.json().get('current_observation')
    req.close()
    rain_last_hour_mm = int(observation['precip_1hr_metric'])
    rain_today_mm = int(observation['precip_today_metric'])
    print("Last hour %dmm, today %dmm" % (rain_last_hour_mm, rain_today_mm))
    return rain_last_hour_mm, rain_today_mm


def _system_on():
    _pulse_relay(WATER_ON_PIN)


def _system_off():
    _pulse_relay(WATER_OFF_PIN)


def _pulse_relay(pin):
    pin.value(1)
    # 10ms minimum time to alter relay latch as per specification of G6SK-2
    utime.sleep_ms(10)
    pin.value(0)


def _battery_voltage():
    adc = ADC(BATTERY_PIN)
    sum = 0
    for x in range(0, ADC_READS):
        sum += adc.read()
    return ADC_REF * RESISTOR_RATIO * \
        (sum / ADC_READS - ADC_OFFSET) / 4096 / 1000


def _sleep_enabled():
    return NO_SLEEP_PIN.value() == 0
