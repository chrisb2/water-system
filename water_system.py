"""Monitor local rainfall and disable garden watering system if required."""
import urequests
from machine import Pin, ADC
import machine
import utime
import urtc
import wifi
import secrets

WAKEUP_PIN = Pin(4, Pin.IN, Pin.PULL_UP)
SCL_PIN = Pin(17)
SDA_PIN = Pin(5)
WATER_ON_PIN = Pin(33, Pin.OUT, Pin.PULL_DOWN, value=0)
WATER_OFF_PIN = Pin(32, Pin.OUT, Pin.PULL_DOWN, value=0)
NO_SLEEP_PIN = Pin(26, Pin.IN, Pin.PULL_DOWN, value=0)
BATTERY_PIN = Pin(34)  # ADC

# External resister divider (ohms)
R1 = 10070000
R2 = 3329000
RESISTOR_RATIO = (R1 + R2) / R2

# ADC reference voltage in millivolts (adjust for each ESP32)
ADC_REF = 1165
# Number of ADC reads to take average of
ADC_READS = 100

_THINGSPEAK_URL = (
    'https://api.thingspeak.com/update'
    '?api_key={}&field1={}&field2={}&field3={}&field4={}&field5={}')
_WEATHER_URL = \
   'http://api.wunderground.com/api/{}/conditions/q{}.json'
_FORECAST_URL = \
   'http://api.wunderground.com/api/{}/geolookup/forecast/q/{}.json'

# 5AM GMT
RTC_ALARM = urtc.datetime_tuple(None, None, None, None, 5, 0, None, None)
# Every hour
# RTC_ALARM = urtc.datetime_tuple(None, None, None, None, None, 0, None, None)
# Every minute
# RTC_ALARM = urtc.datetime_tuple(None, None, None, None, None, None, 0, None)


def run():
    """Main entry point to execute this program."""
    # Set variable so that system defaults to ON avoiding garden never being
    # watered if execution repeatedly fails.
    rainfall = False

    sleep_enabled = _sleep_enabled()

    battery_volts = _battery_voltage()
    try:
        if wifi.connect():
            rain_last_hour_mm, rain_today_mm = _read_weather()
            rain_forecast_today_mm, rain_forecast_tomorrow_mm = _read_forecast()

            rainfall = (rain_today_mm > 3 or rain_last_hour_mm > 1
                        or rain_forecast_today_mm > 1)

            _send_to_thingspeak(rain_last_hour_mm, rain_today_mm,
                                rain_forecast_today_mm, battery_volts,
                                rainfall)
    except Exception:
        # Catch exceptions so that device goes back to sleep if WiFi connect or
        # HTTP calls fail with exceptions
        pass
    finally:
        wifi.disconnect()

    if rainfall:
        _system_off()
    else:
        _system_on()

    if sleep_enabled:
        _sleep_until(RTC_ALARM)


def datetime():
    """Get current date/time from RTC."""
    return _get_rtc().datetime()


def initialize_rtc_from_ntp():
    """Initialize RTC date/time from NTP."""
    rtc = machine.RTC()
    rtc.ntp_sync(server="pool.ntp.org")

    current_time = list(utime.localtime())
    time_to_set = []
    time_to_set.append(current_time[0])  # Year
    time_to_set.append(current_time[1])  # Month
    time_to_set.append(current_time[2])  # Day
    time_to_set.append(current_time[6])  # Weekday
    time_to_set.append(current_time[3])  # Hour
    time_to_set.append(current_time[4])  # Minute
    time_to_set.append(current_time[5])  # Second
    _get_rtc().datetime(time_to_set)


def _sleep_until(alarm_time):
    _configure_pin_interrupt()
    _configure_rtc_alarm(alarm_time)
    print('Sleeping...')
    machine.deepsleep()


def _configure_pin_interrupt():
    rtc = machine.RTC()
    rtc.wake_on_ext0(WAKEUP_PIN, 0)


def _get_rtc():
    i2c = machine.I2C(1, sda=SDA_PIN, scl=SCL_PIN)
    return urtc.DS3231(i2c)


def _configure_rtc_alarm(alarm_time):
    rtc = _get_rtc()

    rtc.alarm(0, alarm=1)  # Clear previous alarm state of RTC
    rtc.interrupt(alarm=1)  # Configure alarm on INT/SQW pin of RTC
    rtc.alarm_time(alarm_time, alarm=1)  # Configure alarm time of RTC


def _send_to_thingspeak(rain_last_hour_mm, rain_today_mm,
                        rain_forecast_today_mm, battery_volts, system_off):
    url = _THINGSPEAK_URL.format(secrets.THINGSPEAK_API_KEY,
                                 rain_last_hour_mm, rain_today_mm,
                                 rain_forecast_today_mm, battery_volts,
                                 int(not system_off))
    req = urequests.get(url)
    req.close()


def _read_weather():
    url = _WEATHER_URL.format(secrets.WUNDERGROUND_API_KEY,
                              secrets.WUNDERGROUND_STATION)
    req = urequests.get(url)
    observation = req.json().get('current_observation')
    req.close()
    rain_last_hour_mm = int(observation['precip_1hr_metric'])
    rain_today_mm = int(observation['precip_today_metric'])
    print("Last hour %dmm, today %dmm" % (rain_last_hour_mm, rain_today_mm))
    return rain_last_hour_mm, rain_today_mm


def _read_forecast():
    url = _FORECAST_URL.format(secrets.WUNDERGROUND_API_KEY,
                               secrets.WUNDERGROUND_LOCATION)
    req = urequests.get(url)
    forecast = req.json()['forecast']['simpleforecast']['forecastday']
    req.close()
    rain_today_mm = int(forecast[0]['qpf_allday']['mm'])
    rain_tomorrow_mm = int(forecast[1]['qpf_allday']['mm'])
    print("Today %dmm, tomorrow %dmm" % (rain_today_mm, rain_tomorrow_mm))
    return rain_today_mm, rain_tomorrow_mm


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
    machine.ADC.vref(vref=ADC_REF)
    adc = ADC(BATTERY_PIN)
    sum = 0
    for x in range(0, ADC_READS):
        sum += adc.read()
    return RESISTOR_RATIO * \
        (sum / ADC_READS) / 1000


def _sleep_enabled():
    return NO_SLEEP_PIN.value() == 0
