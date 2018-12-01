"""Monitor local rainfall and disable garden watering system if required."""
import machine
import utime
import clock
import wifi
import config
from file_logger import File
import weather
import thingspeak


def run():
    """Main entry point to execute this program."""
    try:
        machine.setWDT()
        File.logger().info('%s - Awake: %s', clock.timestamp(),
                           machine.wake_description())
        rainfall = False
        next_wake = config.RTC_ALARM
        sleep_enabled = _sleep_enabled()
        battery_volts = _battery_voltage()

        if wifi.connect():
            File.logger().info('%s - WIFI connected', clock.timestamp())
            machine.RTC().write(0, 0)
            rain_data = weather.get_rain_data()
            rainfall = rain_data.rainfall_occurring()
            thingspeak.send(rain_data, battery_volts)
        else:
            File.logger().info('%s - WIFI connect failed', clock.timestamp())
            if not machine.RTC().read(0):
                File.logger().info('%s - sleeping for %d mins',
                                   clock.timestamp(), config.WIFI_RETRY_MINS)
                machine.RTC().write(0, 1)
                next_wake = clock.datetime()
                next_wake.minute = next_wake.minute + config.WIFI_RETRY_MINS
            else:
                machine.RTC().write(0, 0)

        # If WIFI connect fails, system will default to ON.
        if rainfall:
            File.logger().info('%s - System OFF', clock.timestamp())
            _system_off()
        else:
            File.logger().info('%s - System ON', clock.timestamp())
            _system_on()

    except Exception as ex:
        # Catch exceptions so that device goes back to sleep if WiFi connect or
        # HTTP calls fail with exceptions.
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
