topic            = 'climate'
location         = 'kitchen'
lastTempCelsius  = None
lastHumidPerCent = None
dhtSensor        = dht.DHT22(machine.Pin(0))
mqttClient       = MQTTClient('client',
                              '192.168.1.200',
                               user=cr.username,
                               password=cr.password
                             )

def measAndSendMqtt():
    global lastTempCelsius
    global lastHumidPerCent
    try:
        dhtSensor.measure()
        tempCelsius  = int(dhtSensor.temperature())
        humidPerCent = int(dhtSensor.humidity())
        if tempCelsius != lastTempCelsius or humidPerCent != lastHumidPerCent:
            mqttClient.connect()
            lastTempCelsius  = tempCelsius 
            lastHumidPerCent = humidPerCent

            dataDict = {'location':location
                        ,'data':{'tempCelsius':tempCelsius,
                                 'humidityPerCent:':humidPerCent
                                 }
                        }
            dataJson = json.dumps(dataDict)
            mqttClient.publish(topic,dataJson)
            mqttClient.disconnect()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    try:
        tim = Timer(-1)
        tim.init(period=30000, mode=Timer.PERIODIC, callback=lambda t:measAndSendMqtt())
    except Exception as e:
        print(e)