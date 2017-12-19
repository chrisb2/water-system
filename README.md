# Garden Watering System Controller

This [MicroPython](http://micropython.org/) project on an [ESP32](https://en.wikipedia.org/wiki/ESP32) uses
[Wunderground](https://www.wunderground.com) to determine if
significant rain has fallen in the last day and if so disables the garden watering system to conserve water. It reports the rainfall and system status to [ThingSpeak](https://thingspeak.com).

The project is run off a battery and uses the deep sleep mode of the ESP32 to extend the battery life.

## Usage

Configure a ThingSpeak channel something like:

![ThingSpeak channel](https://github.com/chrisb2/water-system/raw/master/thingspeak-settings.png "ThingSpeak Channel Settings")

Download the [urequests](https://raw.githubusercontent.com/micropython/micropython-lib/master/urequests/urequests.py) HTTP library and create a file called _secrets.py_:
```python
"""Secret values required to connect to services."""
WIFI_SSID = 'XXXXXX'
WIFI_PASSPHRASE = 'XXXXXX'
THINGSPEAK_API_KEY = 'XXXXXX'
WUNDERGROUND_API_KEY = 'XXXXXX'
WUNDERGROUND_STATION = '/NZ/christchurch'
```
and copy with the rest of the python files to the ESP32.
