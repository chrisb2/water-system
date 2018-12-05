"""Real time clock (RTC) utility."""
import machine
import utime
import urtc
import config

_i2c = machine.I2C(config.I2C_PERIPHERAL,
                   sda=config.SDA_PIN, scl=config.SCL_PIN)


def datetime():
    """Get current date/time from RTC.

    The result is an 8-tuple of the format
    (year, month, day, weekday, hour, minute, second, millisecond)
    """
    return _get_rtc().datetime()


def timestamp():
    """Get current date/time from RTC formatted as DD-MM-YYYY HH24:MM:SS."""
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
    rtc = machine.RTC()
    rtc.ntp_sync(server="pool.ntp.org")
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
