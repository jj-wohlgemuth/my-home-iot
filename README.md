# My Home IoT

The goal of this project was to be able to monitor and store humidity and temperature readings from multiple spots within my home WiFi area. Eventually I will use the gathered information to automatically open windows and regulate heaters and stuff.

![Block Diagram](https://user-images.githubusercontent.com/52459869/96334457-42067380-1071-11eb-89f0-df4ec9369ef0.png "Block Diagram")

The project supports a high number of DHT22 sensors without altering the code (If you find out the limiting factor for the max number of sensors let me know). Each sensor is hooked up to a ESP8266 which sends the sensor readings via WiFi to the MQTT broker. A machine in the network runs a MQTT client and parses the sensor readings into a SQL database. A HTML plot file gets generated at a predefined frequency (default: 30 minutes) and uploaded to a web server. 

## Setup
### Bill of materials

The budget for this project was 34.28  Euros. With that I bought:
 * Three DHT22 sensors
 * Five AZDelivery ESP8266 WiFi boards and USB programmers that also serve as power supplies

 With that I built three WiFi temperature and humidity sensors. The remaining two ESP8266s will one day be used for other IoT projects. I'm sure ESP32s do the trick as well but the ESP8266 is cheaper. In Addition you need
 * WiFi
 * A machine that runs Python 3 (I used my Synology DS218j)
 * Some USB power supplies
 * Ideally a web server

### MQTT broker
In order to make this work you need a MQTT broker in your network. I used the [Mosquitto broker package for my Synology NAS.](https://www.paaalm07.at/synology/install-configure-the-mosquitto-mqtt-broker/) It also runs on [Raspberry Pi](https://randomnerdtutorials.com/how-to-install-mosquitto-broker-on-raspberry-pi/) and lots of other systems.


### Sensor

There is lot's of [tutorials](https://randomnerdtutorials.com/esp8266-dht11dht22-temperature-and-humidity-web-server-with-arduino-ide/) on how to connect a DHT22 to a serial input. Just don't forget the 4.7k Ohm resistor and you'll be fine. I crammed the USB programmer and the ESP Board into a little plastic box and glued the sensor to the top of it.

![sensor](https://user-images.githubusercontent.com/52459869/96334017-cc4cd880-106d-11eb-9db7-5ac3adf75466.jpg "sensor")
![sensor](https://user-images.githubusercontent.com/52459869/96334415-fc49ab00-1070-11eb-9fba-55dae1967159.jpg "sensor")

### Micropython

The virgin ESP boards don't run Micropython. You need to [flash the Micropython firmware.](https://docs.micropython.org/en/latest/esp8266/tutorial/intro.html) If you use the AZDelivery boards like me you need to solder an additional button to one of the USB programmers. Before you erase the flash and before you write to the flash you need to press and hold the button while plugging it into your USB port. 

![button](https://user-images.githubusercontent.com/52459869/96334016-cc4cd880-106d-11eb-8b71-ab77c6e2b104.jpg "button")

To erase and write you can use [esptool.py](https://pypi.org/project/esptool/). 
```
pip install esptool
```
Erase your flash:
```
esptool.py --port COM7 erase_flash 
```
Write [firmware binary](http://micropython.org/download/#esp8266) to flash:
```
esptool.py --port COM<YOUR_COM> --baud 460800 write_flash --flash_size=detect 0 <PATH TO BIN>
```

Now the USB Programmer lets you access Micropython via virtual COM Port. You can access the Python shell and the file system. If you're a VSCode user like me check out [Pymakr](!https://marketplace.visualstudio.com/items?itemName=pycom.Pymakr). It's a nice little Micropython development tool. Here's what my *pymakr.conf* looks like  

```json

{
    "address": "COM7",
    "username": "micro",
    "password": "python",
    "sync_folder": "/esp8266/scripts",
    "open_on_start": true,
    "safe_boot_on_upload": false,
    "py_ignore": [
        "pymakr.conf",
        ".vscode",
        ".gitignore",
        ".git",
        "project.pymakr",
        "env",
        "venv"
    ],
    "fast_upload": false
}
```
Make sure you use the right virtual COM Port. With that you should be able to upload the scripts in */esp8266/scripts* to the chip. Next you need to install some libraries using [micro-pip (upip)](https://docs.micropython.org/en/latest/reference/packages.html). In the Micropython shell on your ESP run:

```terminal
upip.install('micropython-umqtt.simple')
```
and 
```terminal
upip.install('micropython-ffilib')
```

In *esp8266\scripts\lib* you find config.py. Make sure to assign a unique location name to each of your ESPs. The temperature and humidity from the sensor is read every 10 seconds. The values are only sent if both changed more than the defined threshold values.  

```python
mqtt_topic = 'climate'
location = 'bedroom'
mqtt_server_ip = '192.168.1.200**'
temperature_threshold_celsius = 0.1
humidity_threshold_percent = 1
dht22_pin = 0
```

In the same folder you need to create a file and call it credentials.py with the following content:

```python
mqtt_password = '***YOUR MQTT PW***'
mqtt_username = '***YOUR MQTT USERNAME***'

ssid = '***YOUR WIFI NAME***'
wifi_password = '***YOUR WIFI PASSWORD***'

```
Once you uploaded the content of */esp8266/scripts* to your ESP it should start sending MQTT packets. You can observe those packets using a MQTT analyzer like [MQTTBox](http://workswithweb.com/mqttbox.html).

```json
{"location": "kitchen", "data": {"humidityPerCent": 42.0, "tempCelsius": 23.1}}
```

### SQL
You'll need a SQL database. I used [MariaDb for Synology.](https://www.synology.com/en-global/knowledgebase/DSM/help/MariaDB10/mariadb) To create the table needed for this project run

```SQL
CREATE DATABASE homeDb

CREATE TABLE homeDb.iot (
    ts TIMESTAMP,
    data JSON,
    topic VARCHAR(100),
    location VARCHAR(100)
);
```
To access and debug my database I used [Dbeaver.](https://dbeaver.io/) 

### Web server 

To host the html plot generated by [Plotly](https://plotly.com/) you need a web server with ftp access. You can set up your own or rent one.

### Python

You need Python 3. To install the needed packages run 

``` pip install -r requirements.txt ```

Use *DS218j/config.py* to customize your settings

```python
plot_interval_seconds = int(60*30) #30 minutes
plot_file_path = 'index.html'
log_file_path = 'log.txt'
html_sub_domain = ''
plot_hours = 24 
mqtt_server_ip = '192.168.1.200'
mqtt_port = 1883
mqtt_ping_seconds = 60
mqtt_topic = 'climate'
```
 Create *DS218j/credentials.py* and enter your credentials

 ```python
mqtt_password = '***YOUR MQTT PW***'
mqtt_username = '***YOUR MQTT USERNAME***'

ftp_host = "***YOUR FTP HOST***"
ftp_user = "***YOUR FTP USER***"
ftp_pwd = "***YOUR FTP PW***"
```

Now run 

```
python DS218j\homeIot.py
```
You should see the MQTT packages coming in, the database being filled, a local index.html file being created and the file being uploaded to your FTP server where you can access it via the subdomain. To have the script run permanently in the background and restart when I reboot my Synology I added
```
cd volume1/**YOURPATH**/my-home-iot/ && /usr/local/bin/python3 ./DS218j/homeIot.py &```
```
to my task scheduler (crontab) at boot up.


## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)

## Sensor gallery
Outside sensor using a 5V power supply inside the housing of an unused lamp.
![outside open](https://user-images.githubusercontent.com/52459869/96334010-c951e800-106d-11eb-9454-86266b4d1d35.jpg "outside open")
![outside closed](https://user-images.githubusercontent.com/52459869/96334012-ca831500-106d-11eb-99c5-bf6f3cc9e3e2.jpg "outside closed")

Kitchen sensor hidden under the fridge.
![kitchen](https://user-images.githubusercontent.com/52459869/96334014-cb1bab80-106d-11eb-8e5c-29c9c3055b32.jpg "kitchen")

Bedroom sensor connected the the USB charging port of my alarm clock.
![bedroom](https://user-images.githubusercontent.com/52459869/96334015-cbb44200-106d-11eb-8b63-3f6ffe508e7c.jpg "bedroom")


