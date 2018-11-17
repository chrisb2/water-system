"""Thingspeak upload."""
from retrier import retry
import file_logger
import machine
import secrets
import clock
import urequests as requests

_THINGSPEAK_URL = (
    'https://api.thingspeak.com/update'
    '?api_key={}&field1={}&field2={}&field3={}&field4={}&field5={}&field6={}')


@retry(Exception, tries=5, delay=2, backoff=2.0, logger=file_logger.LOG)
def send(rain_last_hour_mm, rain_today_mm,
         rain_forecast_today_mm, rain_forecast_tomorrow_mm,
         battery_volts, system_off):
    """Send weather and system information to Thingspeak."""
    machine.resetWDT()
    url = _THINGSPEAK_URL.format(secrets.THINGSPEAK_API_KEY,
                                 rain_last_hour_mm, rain_today_mm,
                                 rain_forecast_today_mm,
                                 rain_forecast_tomorrow_mm,
                                 battery_volts, int(not system_off))
    file_logger.LOG.info('%s - Req to: %s', clock.timestamp(), url)
    with requests.get(url) as response:
        file_logger.LOG.info('%s - HTTP status: %d', clock.timestamp(),
                             response.status_code)
        if response.status_code != 200:
            raise ValueError("HTTP status %d" % response.status_code)
