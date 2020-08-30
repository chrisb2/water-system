"""Weather query module."""
import ure
import gc
import config
from retrier import retry
import urequests as requests
from file_logger import File
import watcher
#  import secrets
import clock

_RAIN_URL = (
   'http://data.ecan.govt.nz/data/78/Rainfall/'
   'Rainfall%20for%20individual%20site/CSV?SiteNo=326512&Period=2_Days')

_FORECAST_URL = \
    'http://{}/New_Zealand/Canterbury/Lincoln/forecast.xml'.format(
        config.YR_API_PROXY)

_time_regex = ure.compile('time from=\"(\d+\-\d+\-\d+)')
_rain_regex = ure.compile('precipitation.*value=\"(\d*\.\d+|\d+)\"')


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
                or self.rain_forecast_today_mm > 1
                or self.rain_forecast_tomorrow_mm > 4)

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
    rain_today_mm, rain_tomorrow_mm = (0.0, 0.0)
    File.logger().info('%s - Req to: %s', clock.timestamp(), _FORECAST_URL)

    with requests.get(_FORECAST_URL) as response:
        File.logger().info('%s - HTTP status: %d', clock.timestamp(),
                           response.status_code)
        if response.status_code == 200:
            time_matched = False
            date = ''
            for line in response.iter_lines():
                gc.collect()
                text = line.decode('utf-8', 'ignore').strip()

                if not time_matched:
                    match_time = _time_regex.search(text)
                    if match_time is not None:
                        date = match_time.group(1)
                        if clock.greater_than_tommorow(date):
                            break
                        time_matched = True
                    continue

                match_rain = _rain_regex.search(text)
                if time_matched and match_rain is not None:
                    time_matched = False
                    mm = float(match_rain.group(1))
                    if clock.equal_to_today(date):
                        rain_today_mm += mm
                    else:
                        rain_tomorrow_mm += mm

        else:
            raise ValueError('HTTP status %d' % response.status_code)

    File.logger().info('%s - Today %.1fmm, tomorrow %.1fmm', clock.timestamp(),
                       rain_today_mm, rain_tomorrow_mm)
    print('Today %.1fmm, tomorrow %.1fmm' % (rain_today_mm, rain_tomorrow_mm))
    return round(rain_today_mm), round(rain_tomorrow_mm)
