"""Thingspeak upload."""
from retrier import retry
import requests
from file_logger import File
import watcher
import secrets
import clock

_URL = (
    'https://api.thingspeak.com/update'
    '?api_key={key}&field1={}&field2={}&field3={}&field4={}'
    '&field5={volts}&field6={status}')


@retry(Exception, tries=5, delay=2, backoff=2.0, logger=File.logger())
def send(rain_data, battery_volts):
    """Send weather and system information to Thingspeak."""
    watcher.feed()
    data_tuple = rain_data.get_data()
    url = _URL.format(key=secrets.THINGSPEAK_API_KEY,
                      *data_tuple, volts=battery_volts,
                      status=int(not rain_data.rainfall_occurring()))
    File.logger().info('%s - Req to: %s', clock.timestamp(), url)
    with requests.get(url) as response:
        File.logger().info('%s - HTTP status: %d', clock.timestamp(),
                           response.status_code)
        if response.status_code != 200:
            raise ValueError("HTTP status %d" % response.status_code)
