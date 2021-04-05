#!/usr/bin/python3

import board
import busio
import digitalio
import adafruit_bme280
import datetime
import time
from influxdb import InfluxDBClient

# Approximate altitude of the sensor above sea level in metres. Used to calculate sea level pressure.
ALTITUDE = 66.0 + 6.0
TAGS = {
    "host": "rpi4-68a7f889"
}

def calculate_slp(measured_pressure, temperature):
    """
    Calculates the Sea Level Pressure from the measured pressure and temperature.
    """
    return measured_pressure * pow((1 - ((0.0065 * ALTITUDE) / (temperature + (0.0065 * ALTITUDE) + 273.15))), -5.257)

def cpu_temperature():
    """
    Reads the current CPU temperature of the RPi
    """
    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
        raw = f.read()
        temp = float(raw) / 1000.0
        return temp

def construct_entry(name, value, tags):
    return {
        "measurement": name,
        "tags": tags,
        "fields": {
            "value": value
        }
    }

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.D5)
bme280 = adafruit_bme280.Adafruit_BME280_SPI(spi, cs)

holdoff = 1.0
while True:
    time.sleep(holdoff)
    try:
        print("Connecting to DB ...")
        client = InfluxDBClient('nuc8i7beh.local', 8086, 'root', 'root', 'environment')
        client.switch_database('environment')
        print("Logging data ...")
        while True:
            # Collect the data
            temperature = bme280.temperature
            humidity = bme280.humidity
            pressure = bme280.pressure
            slpressure = calculate_slp(pressure, temperature)
            # Log the data
            json_body = [
                construct_entry("cpu_temperature", cpu_temperature(), TAGS),
                construct_entry("temperature", temperature, TAGS),
                construct_entry("pressure", pressure, TAGS),
                construct_entry("sea_level_pressure", slpressure, TAGS),
                construct_entry("humidity", humidity, TAGS)
            ]
            client.write_points(json_body)
            time.sleep(2)
            # If we have reached this point successfully, we can reset the holdoff
            holdoff = 1.0
    except KeyboardInterrupt:
        print("Keyboard interrupt")
        break
    except Exception as inst:
        print("Exception occurred")
        print(type(inst))
        print(inst.args)
        print(inst)
        holdoff *= 2
        print("Hold-off increased to {} seconds".format(holdoff))
        continue

print("Program ended")
