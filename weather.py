"""Weather query module."""
import config
import secrets
import gc
import machine
import ure
import urequests as requests
from retrier import retry
import clock
import file_logger

_WEATHER_URL = \
   'http://api.wunderground.com/api/{}/conditions/q{}.json'.format(
       secrets.WUNDERGROUND_API_KEY, config.WUNDERGROUND_STATION)
_FORECAST_URL = \
   'http://api.wunderground.com/api/{}/geolookup/forecast/q/{}.json'.format(
       secrets.WUNDERGROUND_API_KEY, config.WUNDERGROUND_LOCATION)

weather_regex = ure.compile('precip.*metric\":\" ?(([0-9]*[.])?[0-9]+)\"')
forecast_qpf = ure.compile('qpf_allday')
forecast_mm = ure.compile('\"mm\":([ ,0-9]*)')


@retry(Exception, tries=5, delay=2, backoff=2, logger=file_logger.LOG)
def read_weather():
    """Read the current weather."""
    machine.resetWDT()
    rain_last_hour_mm, rain_today_mm = (0, 0)
    file_logger.LOG.info('%s - Req to: %s', clock.timestamp(), _WEATHER_URL)
    results = []
    with requests.get(_WEATHER_URL) as response:
        file_logger.LOG.info('%s - HTTP status: %d', clock.timestamp(),
                             response.status_code)
        if response.status_code == 200:
            for line in response.iter_lines():
                gc.collect()
                match = weather_regex.search(line.decode('UTF-8'))
                if match is not None:
                    results.append(match.group(1))
                    file_logger.LOG.info("%s - %s", clock.timestamp(),
                                         match.group(1))
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


@retry(Exception, tries=5, delay=2, backoff=2.0, logger=file_logger.LOG)
def read_forecast():
    """Read the weather forecast."""
    machine.resetWDT()
    rain_today_mm, rain_tomorrow_mm = (0, 0)
    file_logger.LOG.info('%s - Req to: %s', clock.timestamp(), _FORECAST_URL)

    qpf_allday = False
    results = []
    with requests.get(_FORECAST_URL) as response:
        file_logger.LOG.info('%s - HTTP status: %d', clock.timestamp(),
                             response.status_code)
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
                    file_logger.LOG.info("%s - %s", clock.timestamp(),
                                         match_mm.group(1))
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