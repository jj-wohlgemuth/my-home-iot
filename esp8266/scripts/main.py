#mqtt topic for publishing
topic            = 'climate'
#location of the sensor
location         = 'outside'
#initial values for temp and humid
lastTempCelsius  = 0
lastHumidPerCent = 0
#IP of the mqtt server
mqttServerIp     ='192.168.1.200'
'''To limit the amount of messages we only send data if both temperature and
humidity have changed more than these threshold values'''
tempThreshDeg    = 0.1
humiThreshPerc   = 1

'''Create the instances for the sensor and the mqtt client'''
dhtSensor        = dht.DHT22(machine.Pin(0))
mqttClient       = MQTTClient('client',
                               mqttServerIp,
                               user=cr.username,
                               password=cr.password
                             )

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
        if humiDiff > humiThreshPerc and tempDiff > tempThreshDeg:
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
    '''Will measure and eventually publish every 10 seconds. If you significantly reduce this time
    you risk bricking the chip'''
    try:
        tim = Timer(-1)
        tim.init(period=10000, mode=Timer.PERIODIC, callback=lambda t:measAndSendMqtt())
    except Exception as e:
        print(e)