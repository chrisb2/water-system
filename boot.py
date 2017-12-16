"""This file is executed on every boot (including wake-boot from deepsleep)."""
import gc
import wifi

wifi.connect()
gc.collect()
