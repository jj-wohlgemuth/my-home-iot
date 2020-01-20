topic            = 'climate'
location         = 'kitchen'
lastTempCelsius  = 0
lastHumidPerCent = 0
dhtSensor        = dht.DHT22(machine.Pin(0))
mqttClient       = MQTTClient('client',
                              '192.168.1.200',
                               user=cr.username,
                               password=cr.password
                             )
tempThresh       = 0.1
humiThresh       = 1

def do_connect():
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(cr.ssid, cr.wiPw)
        while not sta_if.isconnected():
            pass
        print('connected with network config:', sta_if.ifconfig())

def measAndSendMqtt():
    global lastTempCelsius
    global lastHumidPerCent
    try:
        do_connect()
        dhtSensor.measure()
        tempCelsius  = dhtSensor.temperature()
        humidPerCent = dhtSensor.humidity()
        tempDiff     = abs(lastTempCelsius-tempCelsius)
        humiDiff     = abs(lastHumidPerCent-humidPerCent)
        if humiDiff > humiThresh and tempDiff > tempThresh:
            mqttClient.connect()
            lastTempCelsius  = tempCelsius 
            lastHumidPerCent = humidPerCent

            dataDict = {'location':location
                        ,'data':{'tempCelsius':tempCelsius,
                                 'humidityPerCent':humidPerCent
                                 }
                        }
            dataJson = json.dumps(dataDict)
            mqttClient.publish(topic,dataJson)
            mqttClient.disconnect()
    except Exception as e:
        print('exception: ' + str(e))

if __name__ == "__main__":
    try:
        tim = Timer(-1)
        tim.init(period=10000, mode=Timer.PERIODIC, callback=lambda t:measAndSendMqtt())
    except Exception as e:
        print(e)