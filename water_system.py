"""Monitor local rainfall and disable garden watering system if required."""
import machine
import utime
import clock
import wifi
import config
import file_logger
import weather
import thingspeak


def run():
    """Main entry point to execute this program."""
    try:
        machine.setWDT()
        file_logger.open()
        file_logger.LOG.info('%s - Awake: %s', clock.timestamp(),
                             machine.wake_description())
        rainfall = False
        sleep_enabled = _sleep_enabled()

        battery_volts = _battery_voltage()
        if wifi.connect():
            file_logger.LOG.info('%s - WIFI connected', clock.timestamp())
            rain_last_hour_mm, rain_today_mm = weather.read_weather()
            rain_forecast_today_mm, rain_forecast_tomorrow_mm = \
                weather.read_forecast()

            rainfall = (rain_today_mm > 3 or rain_last_hour_mm > 1
                        or rain_forecast_today_mm > 1
                        or rain_forecast_tomorrow_mm > 4)

            thingspeak.send(rain_last_hour_mm, rain_today_mm,
                            rain_forecast_today_mm, rain_forecast_tomorrow_mm,
                            battery_volts, rainfall)

        if rainfall:
            file_logger.LOG.info('%s - System OFF', clock.timestamp())
            _system_off()
        else:
            file_logger.LOG.info('%s - System ON', clock.timestamp())
            _system_on()

    except Exception as ex:
        # Catch exceptions so that device goes back to sleep if WiFi connect or
        # HTTP calls fail with exceptions
        file_logger.LOG.exc(ex, '%s - Error', clock.timestamp())
    finally:
        try:
            wifi.disconnect()
            file_logger.LOG.info('%s - WIFI disconnected', clock.timestamp())
        except Exception as ex:
            file_logger.LOG.exc(ex, '%s - WIFI disconnect error',
                                clock.timestamp())

        if sleep_enabled:
            file_logger.LOG.info('%s - Sleeping...', clock.timestamp())
            file_logger.close()
            _sleep_until(config.RTC_ALARM)
        else:
            file_logger.close()


def _sleep_until(alarm_time):
    _configure_pin_interrupt()
    clock.configure_rtc_alarm(alarm_time)
    print('Sleeping...')
    machine.deepsleep()


def _configure_pin_interrupt():
    rtc = machine.RTC()
    rtc.wake_on_ext0(config.WAKEUP_PIN, 0)


def _system_on():
    _pulse_relay(config.WATER_ON_PIN)


def _system_off():
    _pulse_relay(config.WATER_OFF_PIN)


def _pulse_relay(pin):
    pin.value(1)
    # 10ms minimum time to alter relay latch as per specification of G6SK-2
    utime.sleep_ms(10)
    pin.value(0)


def _battery_voltage():
    machine.ADC.vref(vref=config.ADC_REF)
    adc = machine.ADC(config.BATTERY_PIN)
    sum = 0
    for x in range(0, config.ADC_READS):
        sum += adc.read()
    return config.RESISTOR_RATIO * (sum / config.ADC_READS) / 1000


def _sleep_enabled():
    return config.NO_SLEEP_PIN.value() == 0
