"""Monitor local rainfall and disable garden watering system if required."""
import urequests
from machine import Pin, ADC
import machine
import utime
import urtc
import ure
import io
import sys
import gc
import wifi
import secrets
import config

DEBUG = True

WAKEUP_PIN = Pin(4, Pin.IN, Pin.PULL_UP)
SCL_PIN = Pin(17)
SDA_PIN = Pin(5)
WATER_ON_PIN = Pin(33, Pin.OUT, Pin.PULL_DOWN, value=0)
WATER_OFF_PIN = Pin(32, Pin.OUT, Pin.PULL_DOWN, value=0)
NO_SLEEP_PIN = Pin(26, Pin.IN, Pin.PULL_DOWN, value=0)
BATTERY_PIN = Pin(34)  # ADC

# External resister divider (ohms)
RESISTOR_RATIO = (config.R1 + config.R2) / config.R2

# Number of ADC reads to take average of
ADC_READS = 100

_THINGSPEAK_URL = (
    'https://api.thingspeak.com/update'
    '?api_key={}&field1={}&field2={}&field3={}&field4={}&field5={}')
_WEATHER_URL = \
   'http://api.wunderground.com/api/{}/conditions/q{}.json'.format(
       secrets.WUNDERGROUND_API_KEY, config.WUNDERGROUND_STATION)
_FORECAST_URL = \
   'http://api.wunderground.com/api/{}/geolookup/forecast/q/{}.json'.format(
       secrets.WUNDERGROUND_API_KEY, config.WUNDERGROUND_LOCATION)

i2c = machine.I2C(1, sda=SDA_PIN, scl=SCL_PIN)
weather_regex = ure.compile('precip.*metric\":\"([ ,0-9]*)\"')
forecast_regex = ure.compile('qpf_allday.*\n.*\n\s*\"mm\":([ ,0-9]*)\n')


def run():
    """Main entry point to execute this program."""
    # Set variable so that system defaults to ON avoiding garden never being
    # watered if execution repeatedly fails.
    try:
        _log_message('Running')
        rainfall = False
        sleep_enabled = _sleep_enabled()

        battery_volts = _battery_voltage()
        if wifi.connect():
            _log_message('WIFI connected')
            rain_last_hour_mm, rain_today_mm = _read_weather()
            rain_forecast_today_mm, rain_forecast_tomorrow_mm = _read_forecast()

            rainfall = (rain_today_mm > 3 or rain_last_hour_mm > 1
                        or rain_forecast_today_mm > 1)

            _send_to_thingspeak(rain_last_hour_mm, rain_today_mm,
                                rain_forecast_today_mm, battery_volts,
                                rainfall)

        if rainfall:
            _log_message('System OFF')
            _system_off()
        else:
            _log_message('System ON')
            _system_on()

    except Exception as ex:
        # Catch exceptions so that device goes back to sleep if WiFi connect or
        # HTTP calls fail with exceptions
        # pass
        _log_exception_to_file(ex)
    finally:
        try:
            wifi.disconnect()
            _log_message('WIFI disconnected')
        except Exception as ex:
            _log_exception_to_file(ex)

        if sleep_enabled:
            _log_message('Sleeping...')
            _sleep_until(config.RTC_ALARM)


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
    response = None
    try:
        response = urequests.get(url)
    finally:
        if response is not None:
            response.close()


def _read_weather():
    rain_last_hour_mm, rain_today_mm = (0, 0)
    try:
        results = []
        with urequests.get(_WEATHER_URL) as response:
            if response.status_code == 200:
                for line in response.iter_lines():
                    match = weather_regex.search(line.decode('UTF-8'))
                    if match is not None:
                        results.append(match.group(1))
                rain_last_hour_mm = _int_value(results[0])
                rain_today_mm = _int_value(results[1])
    except Exception as ex:
        _log_exception_to_file(ex)
    print("Last hour %dmm, today %dmm" % (rain_last_hour_mm, rain_today_mm))
    return rain_last_hour_mm, rain_today_mm


def _read_forecast():
    rain_today_mm, rain_tomorrow_mm = (0, 0)
    try:
        previous = b''
        results = []
        for chunk in urequests.get(_FORECAST_URL):
            gc.collect()
            part = previous + chunk
            match = forecast_regex.search(part.decode('UTF-8'))
            if match is not None:
                results.append(match.group(1))
                previous = b''
            else:
                previous = chunk
            if len(results) == 2:
                break

        rain_today_mm = _int_value(results[0])
        rain_tomorrow_mm = _int_value(results[1])
    except Exception as ex:
        _log_exception_to_file(ex)
    print("Today %dmm, tomorrow %dmm" % (rain_today_mm, rain_tomorrow_mm))
    return rain_today_mm, rain_tomorrow_mm


def _int_value(attribute):
    """Convert to int, coerce invalid values ('--', '-9999.00') to zero."""
    try:
        val = int(attribute)
        if val < 0:
            val = 0
        return val
    except (ValueError, TypeError):
        return 0


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
    machine.ADC.vref(vref=config.ADC_REF)
    adc = ADC(BATTERY_PIN)
    sum = 0
    for x in range(0, ADC_READS):
        sum += adc.read()
    return RESISTOR_RATIO * (sum / ADC_READS) / 1000


def _sleep_enabled():
    return NO_SLEEP_PIN.value() == 0


def _log_message(message):
    if DEBUG:
        with io.open('system.log', mode='wa') as log_file:
            log_file.write('%s - %s\n' % (_datetime_str(), message))


def _log_exception_to_file(ex):
    if DEBUG:
        with io.open('system.log', mode='wa') as log_file:
            log_file.write('%s\n' % _datetime_str())
            sys.print_exception(ex, log_file)


def _datetime_str():
    return '-'.join(map(str, datetime()))
