"""Weather query module."""
import ure
import gc
from retrier import retry
import requests
from file_logger import File
import watcher
import secrets
import clock

_RAIN_URL = (
   'http://data.ecan.govt.nz/data/78/Rainfall/'
   'Rainfall%20for%20individual%20site/CSV?SiteNo=326512&Period=2_Days')

_FORECAST_URL = \
    'https://api.met.no/weatherapi/locationforecast/2.0/compact?{}'.format(
        secrets.LOCATION)


class RainData:
    """Holds current and forecast rain data."""

    def __init__(self):
        """Constructor."""
        self.rain_last_hour_mm = 0
        self.rain_today_mm = 0
        self.rain_today_mm = 0
        self.rain_tomorrow_mm = 0

    def rainfall_occurring(self):
        """Return True if the data indicated that rain has or will occur."""
        return (self.rain_today_mm > 3 or self.rain_last_hour_mm > 1
                or self.rain_forecast_today_mm > 6
                or self.rain_forecast_tomorrow_mm > 9)

    def get_data(self):
        """Return rain data as a tuple."""
        return (self.rain_last_hour_mm, self.rain_today_mm,
                self.rain_forecast_today_mm, self.rain_forecast_tomorrow_mm)

    def set_from_weather(self, weather):
        """Set rain data from current weather."""
        self.rain_last_hour_mm, self.rain_today_mm = weather

    def set_from_forecast(self, forecast):
        """Set rain data from forecast."""
        self.rain_forecast_today_mm, self.rain_forecast_tomorrow_mm = forecast


def get_rain_data():
    """Get the rain data retrieved from the weather service."""
    data = RainData()
    data.set_from_weather(read_rainfall())
    data.set_from_forecast(read_forecast())
    return data


@retry(Exception, tries=6, delay=2, backoff=2, logger=File.logger())
def read_rainfall():
    """Read todays rainfall."""
    watcher.feed()
    rain_last_hour_mm, rain_today_mm = (0.0, 0.0)
    File.logger().info('%s - Req to: %s', clock.timestamp(), _RAIN_URL)
    with requests.get(_RAIN_URL) as response:
        File.logger().info('%s - HTTP status: %d', clock.timestamp(),
                           response.status_code)
        if response.status_code == 200:
            first_line = True
            for line in response.iter_lines():
                if first_line:
                    first_line = False
                    continue
                gc.collect()
                text = line.decode('utf-8', 'ignore').strip()
                values = text.split(',')
                if len(values) == 3:
                    day = int(values[1].split('/')[0])
                    if day == clock.day_of_month():
                        mm = float(values[2])
                        rain_today_mm += mm
                        rain_last_hour_mm = mm
        else:
            raise ValueError("HTTP status %d" % response.status_code)

    File.logger().info('%s - Last hour %.1fmm, today %.1fmm',
                       clock.timestamp(),
                       rain_last_hour_mm, rain_today_mm)
    print('Last hour %.1fmm, today %.1fmm' %
          (rain_last_hour_mm, rain_today_mm))
    return round(rain_last_hour_mm), round(rain_today_mm)


@retry(Exception, tries=6, delay=2, backoff=2.0, logger=File.logger())
def read_forecast():
    """Read the weather forecast."""
    watcher.feed()

    start_regex = ure.compile(r'timeseries')
    continue_regex = ure.compile(r'\},\{')
    hour_regex = ure.compile(r'next_1_hours')
    precip_regex = ure.compile(r'precipitation_amount\":(\d+\.\d)')
    date_regex = ure.compile(r'time\":\"(\d+-\d+-\d+)T')
    # Large chunk size more performant as less regex's run. Must be less than
    # characters in one timeseries element in the response.
    chunkSize = 1000
    windowSize = chunkSize * 2

    rain_today_mm, rain_tomorrow_mm = (0.0, 0.0)
    window = memoryview(bytearray(windowSize))
    emptyChunk = bytes(chunkSize)
    periodFound, hourFound, precipFound, dateFound = False, False, False, False

    File.logger().info('%s - Req to: %s', clock.timestamp(), _FORECAST_URL)
    with requests.get(_FORECAST_URL,
                      headers=secrets.HEADER) as response:
        File.logger().info('%s - HTTP status: %d', clock.timestamp(),
                           response.status_code)
        if response.status_code == 200 or response.status_code == 203:
            for chunk in response.iter_content(chunkSize):
                # Populate response window
                window[0:chunkSize] = window[chunkSize:windowSize]
                if len(chunk) == chunkSize:
                    window[chunkSize:windowSize] = chunk
                else:
                    # last chunk is short
                    window[chunkSize:windowSize] = emptyChunk
                    window[chunkSize:chunkSize+len(chunk)] = chunk
                # print(window)
                windowBytes = bytes(window)  # regex requires bytes
                # Gather precipitation data
                if continue_regex.search(windowBytes) or\
                   start_regex.search(windowBytes):
                    periodFound = True
                if periodFound and hour_regex.search(windowBytes):
                    hourFound = True
                if periodFound and not dateFound:
                    if (dateGroup := date_regex.search(windowBytes)):
                        dateFound = True
                        date = dateGroup.group(1).decode()
                if hourFound and not precipFound:
                    if (precipGroup := precip_regex.search(windowBytes)):
                        precipFound = True
                        mm = float(precipGroup.group(1))
                if dateFound and precipFound:
                    periodFound, hourFound = False, False
                    dateFound, precipFound = False, False
                    # print(date, mm)
                    if clock.greater_than_tommorow(date):
                        break
                    elif clock.equal_to_today(date):
                        rain_today_mm += mm
                    else:
                        rain_tomorrow_mm += mm
        else:
            raise ValueError('HTTP status %d' % response.status_code)

    File.logger().info('%s - Today %.1fmm, tomorrow %.1fmm', clock.timestamp(),
                       rain_today_mm, rain_tomorrow_mm)
    print('Today %.1fmm, tomorrow %.1fmm' % (rain_today_mm, rain_tomorrow_mm))
    return round(rain_today_mm), round(rain_tomorrow_mm)
