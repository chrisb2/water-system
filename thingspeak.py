"""Thingspeak upload."""
from retrier import retry
import requests
from file_logger import File
import watcher
import secrets
import clock

_URL = (
    'https://api.thingspeak.com/update.json'
    '?api_key={key}&field1={f1}&field2={f2}&field3={f3}&field4={f4}'
    '&field5={volts}&field6={status}')


@retry(Exception, tries=5, delay=2, backoff=2.0, logger=File.logger())
def send(rain_data, battery_volts):
    """Send weather and system information to Thingspeak."""
    watcher.feed()
    data = rain_data.get_data()
    url = _URL.format(key=secrets.THINGSPEAK_API_KEY,
                      f1=data[0], f2=data[1], f3=data[2], f4=data[3],
                      volts=battery_volts,
                      status=int(not rain_data.rainfall_occurring()))
    File.logger().info('%s - Req to: %s', clock.timestamp(), url)
    with requests.get(url) as response:
        File.logger().info('%s - HTTP status: %d', clock.timestamp(),
                           response.status_code)
        if response.status_code != 200:
            raise ValueError("HTTP status %d" % response.status_code)
