"""Real time clock (RTC) utility."""
import machine
import utime
import urtc
import ntptime
import config

_SECS_IN_HOUR = 3600
_SECS_IN_DAY = 24 * _SECS_IN_HOUR

_i2c = machine.SoftI2C(sda=config.SDA_PIN, scl=config.SCL_PIN)


def datetime():
    """Get the current timezone date/time from RTC.

    The result is an 8-tuple of the format
    (year, month, day, weekday, hour, minute, second, millisecond)
    """
    gmt_secs = urtc.tuple2seconds(gmt())
    gmt_secs += config.HOURS_DIFF_FROM_GMT * _SECS_IN_HOUR
    return urtc.seconds2tuple(int(gmt_secs))


def gmt():
    """Get current GMT date/time from RTC.

    The result is an 8-tuple of the format
    (year, month, day, weekday, hour, minute, second, millisecond)
    """
    return _get_rtc().datetime()


def day_of_month(days_in_future=0):
    """Get the day of the month."""
    secs = urtc.tuple2seconds(datetime())
    secs += days_in_future * _SECS_IN_DAY
    future = urtc.seconds2tuple(int(secs))
    return future[2]


def greater_than_tommorow(date):
    secs = urtc.tuple2seconds(datetime()) + _SECS_IN_DAY

    year, month, day = date.split('-')
    curr = urtc.datetime_tuple(int(year), int(month), int(day), 0, 0, 0, 0, 0)
    curr_sec = urtc.tuple2seconds(curr)

    return curr_sec > secs


def equal_to_today(date):
    dt = datetime()
    today = urtc.datetime_tuple(dt.year, dt.month, dt.day, 0, 0, 0, 0, 0)
    secs = urtc.tuple2seconds(today)

    year, month, day = date.split('-')
    curr = urtc.datetime_tuple(int(year), int(month), int(day), 0, 0, 0, 0, 0)
    curr_sec = urtc.tuple2seconds(curr)

    return curr_sec == secs


def timestamp():
    """Get current timezone date/time from RTC as DD-MM-YYYY HH24:MM:SS."""
    dt = datetime()
    return '%02d-%02d-%d %02d:%02d:%02d' % \
           (dt.day, dt.month, dt.year, dt.hour, dt.minute, dt.second)


def future(minutes):
    """Get a date time in the future by the specified minutes."""
    dt = datetime()
    return urtc.datetime_tuple(None, None, None, None, None,
                               dt.minute + minutes, None, None)


def initialize_rtc_from_ntp():
    """Initialize RTC date/time from NTP."""
    ntptime.settime()
    utime.sleep(5)

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


def configure_rtc_alarm(alarm_time):
    """Configure alarm time of RTC."""
    rtc = _get_rtc()
    rtc.alarm(0, alarm=1)  # Clear previous alarm state of RTC
    rtc.interrupt(alarm=1)  # Configure alarm on INT/SQW pin of RTC
    rtc.alarm_time(alarm_time, alarm=1)  # Configure alarm time of RTC


def _get_rtc():
    return urtc.DS3231(_i2c)
