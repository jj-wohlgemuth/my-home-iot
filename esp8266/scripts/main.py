def sendMqtt(topic,message):
    print('doing it')
    try:
        c = MQTTClient('client', '192.168.1.200', user=cr.username, password=cr.password)
        c.connect()
        c.publish(topic,message)
        c.disconnect()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    try:
        tim = Timer(-1)
        print()
        #tim.init(period=5000, mode=Timer.PERIODIC, callback=lambda t:main())
        sendMqtt(b'climate',b'test')
    except Exception as e:
        print(e)