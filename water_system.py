"""Monitor local rainfall and disable garden watering system if required."""
import urequests as requests
from machine import Pin, ADC
import machine
import utime
import urtc
import ure
import io
import gc
import wifi
import secrets
import config
import logging
from retrier import retry

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
    '?api_key={}&field1={}&field2={}&field3={}&field4={}&field5={}&field6={}')
_WEATHER_URL = \
   'http://api.wunderground.com/api/{}/conditions/q{}.json'.format(
       secrets.WUNDERGROUND_API_KEY, config.WUNDERGROUND_STATION)
_FORECAST_URL = \
   'http://api.wunderground.com/api/{}/geolookup/forecast/q/{}.json'.format(
       secrets.WUNDERGROUND_API_KEY, config.WUNDERGROUND_LOCATION)

i2c = machine.I2C(config.I2C_PERIPHERAL, sda=SDA_PIN, scl=SCL_PIN)
weather_regex = ure.compile('precip.*metric\":\" ?(([0-9]*[.])?[0-9]+)\"')
forecast_qpf = ure.compile('qpf_allday')
forecast_mm = ure.compile('\"mm\":([ ,0-9]*)')

_stream = None
_log = None


def run():
    """Main entry point to execute this program."""
    try:
        global _log
        machine.setWDT()
        _log = _initialize_logger()
        _log.info('%s - Running', _timestamp())
        rainfall = False
        sleep_enabled = _sleep_enabled()

        battery_volts = _battery_voltage()
        if wifi.connect():
            _log.info('%s - WIFI connected', _timestamp())
            rain_last_hour_mm, rain_today_mm = _read_weather()
            rain_forecast_today_mm, rain_forecast_tomorrow_mm = \
                _read_forecast()

            rainfall = (rain_today_mm > 3 or rain_last_hour_mm > 1
                        or rain_forecast_today_mm > 1
                        or rain_forecast_tomorrow_mm > 4)

            _send_to_thingspeak(rain_last_hour_mm, rain_today_mm,
                                rain_forecast_today_mm,
                                rain_forecast_tomorrow_mm,
                                battery_volts, rainfall)

        if rainfall:
            _log.info('%s - System OFF', _timestamp())
            _system_off()
        else:
            _log.info('%s - System ON', _timestamp())
            _system_on()

    except Exception as ex:
        # Catch exceptions so that device goes back to sleep if WiFi connect or
        # HTTP calls fail with exceptions
        _log.exc(ex, '%s', _timestamp())
    finally:
        try:
            wifi.disconnect()
            _log.info('%s - WIFI disconnected', _timestamp())
        except Exception as ex:
            _log.exc(ex, '%s', _timestamp())

        if sleep_enabled:
            _log.info('%s - Sleeping...', _timestamp())
            _close_logger()
            _sleep_until(config.RTC_ALARM)
        else:
            _close_logger()


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


@retry(Exception, tries=5, delay=2, backoff=1.5, logger=_log)
def _send_to_thingspeak(rain_last_hour_mm, rain_today_mm,
                        rain_forecast_today_mm, rain_forecast_tomorrow_mm,
                        battery_volts, system_off):
    machine.resetWDT()
    url = _THINGSPEAK_URL.format(secrets.THINGSPEAK_API_KEY,
                                 rain_last_hour_mm, rain_today_mm,
                                 rain_forecast_today_mm,
                                 rain_forecast_tomorrow_mm,
                                 battery_volts, int(not system_off))
    _log.info('%s - Req to: %s',  _timestamp(), url)
    with requests.get(url) as response:
        _log.info('%s - HTTP status: %d', _timestamp(), response.status_code)
        if response.status_code != 200:
            raise ValueError("HTTP status %d" % response.status_code)


@retry(Exception, tries=5, delay=2, backoff=2, logger=_log)
def _read_weather():
    machine.resetWDT()
    rain_last_hour_mm, rain_today_mm = (0, 0)
    _log.info('%s - Req to: %s', _timestamp(), _WEATHER_URL)
    results = []
    with requests.get(_WEATHER_URL) as response:
        _log.info('%s - HTTP status: %d', _timestamp(), response.status_code)
        if response.status_code == 200:
            for line in response.iter_lines():
                gc.collect()
                match = weather_regex.search(line.decode('UTF-8'))
                if match is not None:
                    results.append(match.group(1))
                    _log.info("%s - %s", _timestamp(), match.group(1))
                if len(results) == 2:
                    rain_last_hour_mm = _int_value(results[0])
                    rain_today_mm = _int_value(results[1])
                    break

            if len(results) != 2:
                raise ValueError("Only %d values found" % len(results))
        else:
            raise ValueError("HTTP status %d" % response.status_code)

    print("Last hour %dmm, today %dmm" % (rain_last_hour_mm, rain_today_mm))
    return rain_last_hour_mm, rain_today_mm


@retry(Exception, tries=5, delay=2, backoff=1.5, logger=_log)
def _read_forecast():
    machine.resetWDT()
    rain_today_mm, rain_tomorrow_mm = (0, 0)
    _log.info('%s - Req to: %s', _timestamp(), _FORECAST_URL)

    qpf_allday = False
    results = []
    with requests.get(_FORECAST_URL) as response:
        _log.info('%s - HTTP status: %d', _timestamp(), response.status_code)
        if response.status_code == 200:
            for line in response.iter_lines():
                gc.collect()
                text = line.decode('utf-8', 'ignore').strip()

                if not qpf_allday:
                    match_qpf = forecast_qpf.search(text)
                    if match_qpf is not None:
                        qpf_allday = True
                    continue

                match_mm = forecast_mm.search(text)
                if qpf_allday and match_mm is not None:
                    results.append(match_mm.group(1))
                    _log.info("%s - %s", _timestamp(), match_mm.group(1))
                    qpf_allday = False

                    if len(results) == 2:
                        rain_today_mm = _int_value(results[0])
                        rain_tomorrow_mm = _int_value(results[1])
                        break

            if len(results) != 2:
                raise ValueError("Only %d values found" % len(results))
        else:
            raise ValueError("HTTP status %d" % response.status_code)

    print("Today %dmm, tomorrow %dmm" % (rain_today_mm, rain_tomorrow_mm))
    return rain_today_mm, rain_tomorrow_mm


def _int_value(attribute):
    """Convert to int.

    Invalid values ('--', '-9999.00', etc) cause ValueError or TypeError
    """
    val = int(attribute)
    if val < 0:
        raise ValueError("Negative value: %d" % val)
    return val


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


def _timestamp():
    dt = datetime()
    return '%d-%02d-%02d %02d:%02d:%02d' % \
           (dt[0], dt[1], dt[2], dt[4], dt[5], dt[6])


def _initialize_logger():
    global _stream
    _stream = io.open('system.log', mode='wa')
    logging.basicConfig(level=logging.INFO, stream=_stream)
    return logging.getLogger("system")


def _close_logger():
    global _stream
    if _stream is not None:
        _stream.close()
