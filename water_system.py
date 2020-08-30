"""Monitor local rainfall and disable garden watering system if required."""
import machine
import esp32
import utime
import clock
import wifi
import config
from file_logger import File
import weather
import watcher
import thingspeak


def run():
    """Main entry point to execute this program."""
    try:
        File.logger().info('%s - Awake: %s', clock.timestamp(),
                           machine.wake_reason())
        rainfall = False
        next_wake = config.RTC_ALARM
        sleep_enabled = _sleep_enabled()
        battery_volts = _battery_voltage()

        if not sleep_enabled:
            watcher.disable()

        if wifi.connect():
            _resetConnectCount()
            File.logger().info('%s - WIFI connected', clock.timestamp())
            rain_data = weather.get_rain_data()
            rainfall = rain_data.rainfall_occurring()
            thingspeak.send(rain_data, battery_volts)

            if rainfall:
                File.logger().info('%s - System OFF', clock.timestamp())
                _system_off()
            else:
                File.logger().info('%s - System ON', clock.timestamp())
                _system_on()
        else:
            if _incrementConnectCount() > 5:
                # Give up trying to connect to WiFi
                _resetConnectCount()
            else:
                File.logger().info('%s - Set one minute sleep, attempts %d',
                                   clock.timestamp(), _getConnectCount())
                next_wake = config.SLEEP_ONE_MINUTE

    except Exception as ex:
        # Catch exceptions so that device goes back to sleep HTTP calls
        # fail with exceptions.
        File.logger().exc(ex, '%s - Error', clock.timestamp())
    finally:
        try:
            wifi.disconnect()
            File.logger().info('%s - WIFI disconnected', clock.timestamp())
        except Exception as ex:
            File.logger().exc(ex, '%s - WIFI disconnect error',
                              clock.timestamp())

        if sleep_enabled:
            File.logger().info('%s - Sleeping...', clock.timestamp())
            File.close_log()
            _sleep_until(next_wake)
        else:
            File.close_log()


def _sleep_until(alarm_time):
    _configure_pin_interrupt()
    clock.configure_rtc_alarm(alarm_time)
    print('Sleeping...')
    machine.deepsleep()


def _configure_pin_interrupt():
    esp32.wake_on_ext0(pin=config.WAKEUP_PIN, level=esp32.WAKEUP_ALL_LOW)


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
    adc = machine.ADC(config.BATTERY_PIN)
    sum = 0
    for x in range(0, config.ADC_READS):
        sum += adc.read()
    return (sum / config.ADC_READS) / 4096 * \
        config.ADC_FACTOR * config.RESISTOR_RATIO


def _sleep_enabled():
    return config.NO_SLEEP_PIN.value() == 0


def _getConnectCount():
    val = machine.RTC().memory()[0]
    if val is not None:
        return val
    else:
        machine.RTC().memory(bytes([0]))
        return 0


def _incrementConnectCount():
    val = _getConnectCount() + 1
    machine.RTC().memory(bytes([val]))
    return val


def _resetConnectCount():
    machine.RTC().memory(bytes([0]))
