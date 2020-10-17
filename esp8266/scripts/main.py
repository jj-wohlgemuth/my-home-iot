import esp
import upip
from umqtt.robust import MQTTClient
from machine import Timer
import json
import dht
import machine
import network
import config as cf
import credentials as cr

last_temp_celsius = -273
last_humidity_percent = 0

sta_if = network.WLAN(network.STA_IF)
dht_sensor = dht.DHT22(machine.Pin(cf.dht22_pin))
mqttClient = MQTTClient('client',
                        cf.mqtt_server_ip,
                        user=cr.mqtt_username,
                        password=cr.mqtt_password
                        )


def do_connect():
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(cr.ssid, cr.wifi_password)
        while not sta_if.isconnected():
            pass
        print('connected with network config:', sta_if.ifconfig())


def measure():
    temp_celsius = None
    humidity_percent = None
    try:
        do_connect()
        dht_sensor.measure()
        temp_celsius = dht_sensor.temperature()
        humidity_percent = dht_sensor.humidity()
    except Exception as e:
        print('exception: ' + str(e))
    return temp_celsius, humidity_percent


def send(temp_celsius, humidity_percent):
    global last_temp_celsius
    global last_humidity_percent
    try:
        temp_diff_celsius = abs(last_temp_celsius-temp_celsius)
        humi_diff_percent = abs(last_humidity_percent-humidity_percent)
        if humi_diff_percent > cf.humidity_threshold_percent and\
           temp_diff_celsius > cf.temperature_threshold_celsius:
            mqttClient.connect()
            last_temp_celsius = temp_celsius
            last_humidity_percent = humidity_percent
            data_dict = {'location': cf.location,
                         'data': {
                                'tempCelsius': temp_celsius,
                                'humidityPerCent': humidity_percent
                            }
                         }
            data_json = json.dumps(data_dict)
            mqttClient.publish(cf.mqtt_topic, data_json)
            mqttClient.disconnect()
    except Exception as e:
        print('exception: ' + str(e))


def measure_send():
    temp_celsius, humidity_percent = measure()
    send(temp_celsius, humidity_percent)


if __name__ == "__main__":
    '''Will measure and eventually publish every 10 seconds.
    If you significantly reduce this time
    you risk bricking the chip'''
    try:
        tim = Timer(-1)
        tim.init(period=10000,
                 mode=Timer.PERIODIC,
                 callback=lambda t: measure_send()
                 )
    except Exception as e:
        print(e)
