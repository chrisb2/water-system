"""Monitor local rainfall and disable garden watering system if required."""
import urequests
import machine
import ntptime
import utime
import secrets

_THINGSPEAK_URL = ('https://api.thingspeak.com/update?api_key={}'
                   '&field1={}&field2={}')
_WEATHER_URL = \
    "http://api.wunderground.com/api/{}/conditions/q{}.json"


def run():
    """Main entry point to execute this program."""
    rain_last_hour_mm, rain_today_mm = _read_from_wunderground()
    _send_to_thingspeak(rain_last_hour_mm, rain_today_mm)
    print("Last hour %dmm, today %dmm" % (rain_last_hour_mm, rain_today_mm))
    machine.deepsleep(_sleep_ms())


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


def _sleep_ms():
    ntptime.settime()

    current_secs = utime.time()
    current_time = list(utime.localtime(current_secs))
    # current_time[2] = current_time[2] + 1  # increment day
    current_time[3] = current_time[3] + 1  # increment hour
    current_time[4] = 0  # Set minutes to zero
    current_time[5] = 0  # Set seconds to zero

    next_secs = utime.mktime(tuple(current_time))
    return (next_secs - current_secs) * 1000
