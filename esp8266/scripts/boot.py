# This file is executed on every boot (including wake-boot from deepsleep)
import esp
import upip
from umqtt.robust import MQTTClient
from machine import Timer
import credentials as cr
import json
import dht
import machine
import network
network.WLAN(network.AP_IF).active(False)
sta_if = network.WLAN(network.STA_IF)