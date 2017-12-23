"""Monitor local rainfall and disable garden watering system if required."""
import urequests
import machine
import esp32
import urtc
import secrets

INTERRUPT_PIN = machine.Pin(4)
SCL_PIN = machine.Pin(17)
SDA_PIN = machine.Pin(5)

_THINGSPEAK_URL = ('https://api.thingspeak.com/update?api_key={}'
                   '&field1={}&field2={}')
_WEATHER_URL = \
    'http://api.wunderground.com/api/{}/conditions/q{}.json'

# 5AM GMT
RTC_ALARM = urtc.datetime_tuple(None, None, None, None, 5, 0, None, None)


def run():
    """Main entry point to execute this program."""
    rain_last_hour_mm, rain_today_mm = _read_from_wunderground()
    _send_to_thingspeak(rain_last_hour_mm, rain_today_mm)
    print("Last hour %dmm, today %dmm" % (rain_last_hour_mm, rain_today_mm))

    _sleep_until(RTC_ALARM)


def _sleep_until(alarm_time):
    _configure_pin_interrupt()
    _configure_rtc_alarm(alarm_time)
    machine.deepsleep()


def _configure_pin_interrupt():
    pin = INTERRUPT_PIN
    pin.init(pin.IN, pin.PULL_UP)
    esp32.wake_on_ext0(pin, 0)


def _configure_rtc_alarm(alarm_time):
    i2c = machine.I2C(-1, SCL_PIN, SDA_PIN)
    rtc = urtc.DS3231(i2c)

    rtc.alarm(0, alarm=1)  # Clear previous alarm state of RTC
    rtc.interrupt(alarm=1)  # Configure alarm on INT/SQW pin of RTC
    rtc.alarm_time(alarm_time, alarm=1)  # Configure alarm time of RTC


def _send_to_thingspeak(rain_last_hour_mm, rain_today_mm):
    url = _THINGSPEAK_URL.format(secrets.THINGSPEAK_API_KEY,
                                 rain_last_hour_mm, rain_today_mm)
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
    return rain_last_hour_mm, rain_today_mm
