# Garden Watering System Controller

This [MicroPython](http://micropython.org/) project on an [ESP32](https://en.wikipedia.org/wiki/ESP32) uses
weather API's to determine if significant rain has fallen in the last day, or
is forecast today, and if so disables the garden watering system to conserve
water. It reports the rainfall and system status to [ThingSpeak](https://thingspeak.com).

The project is run off a single 1600mAh LiFePO4 battery (18650) and uses the
deep sleep mode of the ESP32 to extend the battery life.

This controller is suitable for use with automatic watering systems which expose
the ability to disable the system by making a connection open circuit.

## Schematic

If the schematic appears to be missing details, download it and view it locally,
or zoom the web page.

![Circuit Schematic](./schematic-garden-watering-controller.svg)

## Container

I used a polycarbonate box with a build-in O-ring seal. A
[PTFE breathable vent](https://nicegear.nz/product/waterproof-breathable-enclosure-vent)
was fitted to allow air, but not water vapor in and out. The electrical
connections exiting the container to the watering system must be completely
sealed.

## Weather API's

All weather API calls and rain calculations are in _weather.py_, you will need
to update the services called and the code used to extract data from the
responses.

## Usage

Configure a ThingSpeak channel something like:

![ThingSpeak channel](https://github.com/chrisb2/water-system/raw/master/thingspeak-settings.png "ThingSpeak Channel Settings")

Download the library:
* [urtc](https://raw.githubusercontent.com/chrisb2/Adafruit-uRTC/master/urtc.py) real time clock (RTC) library.
* [urequests](https://github.com/micropython/micropython-lib/blob/cfca9b4f9096f0fe1c0eeefead25c1d5994e1b64/urequests/urequests.py) library which supports large responses.

Create a file called _secrets.py_ and fill in appropriate values:
```python
"""Secret values required to connect to services."""
WIFI_SSID = 'XXXXXX'
WIFI_PASSPHRASE = 'XXXXXX'
THINGSPEAK_API_KEY = 'XXXXXX'

YR_HEADER = {'User-Agent': 'XXXX'}
YR_LOCATION = 'lat=-XX.XXX&lon=YYY.YYY'
```
By default the RTC will wake the ESP32 from deep sleep at 5am GMT every day, if
you want a different time edit the value of the _RTC_ALARM_ constant in
_config.py_.

Copy all the python files to the ESP32.

Set the 'No Sleep' DIP switch to 'on', press the RST button to reset the ESP32,
then connect using Putty or similar serial client and initialize the RTC by
executing the following:
```python
import wifi
import clock

wifi.connect()
clock.initialize_rtc_from_ntp()

# Get date time, to verify setting.
clock.timestamp()
```
Set the 'No Sleep' DIP switch to 'off', press the RST button to reset the ESP32
and connect to your water system.
