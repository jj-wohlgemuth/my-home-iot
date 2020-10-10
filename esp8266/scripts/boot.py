# This file is executed on every boot (including wake-boot from deepsleep)
import network
network.WLAN(network.AP_IF).active(False)
